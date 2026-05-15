"""
Module: ingestion/indexer.py
Date: 2026-05-08

Embeds Document chunks and stores them in a vector database.

The vector database backend is determined by vectorstore.provider in
config.yaml. Currently supported: "chroma". To add a new provider, implement
VectorDBManager and register it in ingestion/vectordb.py.

Public API:
    get_collection_count(business_key) -> int
    index_documents(docs, business_key) -> int   # returns chunk count
    clear_collection(business_key) -> None
"""

import hashlib
import logging

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from config.settings import settings
from ingestion.vectordb import get_vector_db, VectorDBManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_embedder() -> OpenAIEmbeddings:
    """Return an OpenAIEmbeddings instance using the configured model."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def _resolve_collection_name(business_key: str) -> str:
    """Return the collection name for a business key.

    The key is used directly as the collection name. Collections are
    created at app startup via ensure_collection.
    """
    return business_key


def _make_chunk_id(doc: Document, position: int) -> str:
    """Generate a stable, unique ID for a chunk.

    SHA-256 of source path + position — same file always produces the same
    IDs so re-ingestion is idempotent (upsert, not duplicate).
    """
    source = doc.metadata.get("source", "unknown")
    raw = f"{source}::{position}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_collection_count(business_key: str) -> int:
    """Return the number of indexed vectors for a business collection.

    Args:
        business_key: Short key from config (e.g. 'cafe', 'hotel', 'gems').

    Returns:
        Total number of indexed chunks.

    Raises:
        KeyError: If business_key is not in the configured collections.
    """
    collection_name = _resolve_collection_name(business_key)
    db: VectorDBManager = get_vector_db()
    db.ensure_collection(collection_name)
    return db.count(collection_name)


def index_documents(docs: list[Document], business_key: str) -> int:
    """Embed and upsert a list of Documents into the vector store.

    The upsert strategy means calling this function multiple times with the
    same documents is idempotent — existing chunks are updated, not duplicated.

    Args:
        docs:         List of chunked Documents to embed and store.
        business_key: Which collection to store into ('cafe', 'hotel', 'gems').

    Returns:
        Number of chunks indexed.

    Raises:
        KeyError:   If business_key is not configured.
        ValueError: If docs is empty.
    """
    if not docs:
        raise ValueError("docs must not be empty — nothing to index.")

    collection_name = _resolve_collection_name(business_key)
    db: VectorDBManager = get_vector_db()
    db.ensure_collection(collection_name)

    embedder = _get_embedder()
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]
    ids = [_make_chunk_id(doc, i) for i, doc in enumerate(docs)]

    logger.info("Embedding %d chunks for '%s'...", len(texts), business_key)
    vectors = embedder.embed_documents(texts)

    db.upsert(
        collection_name=collection_name,
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )

    logger.info("Indexed %d chunks into '%s'.", len(docs), business_key)
    return len(docs)


def list_documents(business_key: str) -> list[dict]:
    """Return per-source-file chunk counts for a business collection.

    Returns:
        List of {"name": str, "chunks": int} sorted by name.
    """
    collection_name = _resolve_collection_name(business_key)
    db: VectorDBManager = get_vector_db()
    db.ensure_collection(collection_name)
    chroma_col = db._get_collection(collection_name)
    result = chroma_col.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for meta in result.get("metadatas") or []:
        source = (meta or {}).get("source", "unknown")
        name = source.split("/")[-1].split("\\")[-1]
        counts[name] = counts.get(name, 0) + 1
    return [{"name": k, "chunks": v} for k, v in sorted(counts.items())]


def list_all_collections() -> list[str]:
    """Return the names of all collections that exist in the vector DB."""
    db: VectorDBManager = get_vector_db()
    return sorted(col.name for col in db._db.list_collections())


def drop_collection(business_key: str) -> None:
    """Permanently delete an entire collection and all its documents.

    Args:
        business_key: Collection key to drop (must not be a configured key).
    """
    collection_name = _resolve_collection_name(business_key)
    db: VectorDBManager = get_vector_db()
    db.delete_collection(collection_name)
    logger.info("Dropped collection '%s'.", collection_name)


def rename_collection(old_key: str, new_key: str) -> None:
    """Copy all vectors from old_key collection to new_key, then drop old.

    ChromaDB does not support native rename, so we copy all embeddings,
    documents and metadatas into a new collection then delete the old one.

    Args:
        old_key: Existing collection key.
        new_key: Destination collection key (must not already exist).
    """
    old_name = _resolve_collection_name(old_key)
    new_name = _resolve_collection_name(new_key)
    db: VectorDBManager = get_vector_db()
    old_col = db._get_collection(old_name)
    data = old_col.get(include=["embeddings", "documents", "metadatas"])
    db.ensure_collection(new_name)
    if data.get("ids"):
        db.upsert(
            new_name,
            data["ids"],
            data["embeddings"],
            data["documents"],
            data["metadatas"],
        )
    db.delete_collection(old_name)
    logger.info("Renamed collection '%s' → '%s'.", old_name, new_name)


def delete_document(business_key: str, filename: str) -> int:
    """Delete all chunks belonging to a specific document from the collection.

    Args:
        business_key: Short key from config (e.g. 'luster', 'solar_stay').
        filename: The original filename (basename only) to remove.

    Returns:
        Number of chunks deleted.
    """
    collection_name = _resolve_collection_name(business_key)
    db: VectorDBManager = get_vector_db()
    db.ensure_collection(collection_name)
    chroma_col = db._get_collection(collection_name)
    result = chroma_col.get(include=["metadatas"])
    ids_to_delete = []
    for doc_id, meta in zip(result.get("ids") or [], result.get("metadatas") or []):
        source = (meta or {}).get("source", "")
        name = source.split("/")[-1].split("\\")[-1]
        if name == filename:
            ids_to_delete.append(doc_id)
    if ids_to_delete:
        chroma_col.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def clear_collection(business_key: str) -> None:
    """Delete and recreate the collection for the given business key.

    Use this before a full re-index to start from a clean state.

    Args:
        business_key: Short key from config (e.g. 'cafe', 'hotel', 'gems').

    Raises:
        KeyError: If business_key is not in the configured collections.
    """
    collection_name = _resolve_collection_name(business_key)
    db: VectorDBManager = get_vector_db()
    db.clear_collection(collection_name)
    logger.info("Cleared collection for '%s'.", business_key)
