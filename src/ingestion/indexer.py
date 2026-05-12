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
    """Map a short business key to its full collection name from config.

    Raises:
        KeyError: If the business_key is not in the configured collections.
    """
    collections: dict[str, str] = settings.collections
    if business_key not in collections:
        valid = list(collections.keys())
        raise KeyError(
            f"Unknown business key '{business_key}'. Valid keys: {valid}"
        )
    return collections[business_key]


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
