"""
Module: ingestion/indexer.py
Date: 2026-05-08

Embeds Document chunks and stores them in ChromaDB.

Responsibilities:
  - Build a ChromaDB client pointed at the configured persist directory.
  - Embed text using OpenAI's text-embedding-3-small via LangChain.
  - Upsert chunks into a per-business collection so re-ingestion is
    idempotent (same chunk_id → update in place, not duplicate).
  - Expose a thin API used by both the CLI ingestion pipeline and tests.

Public API:
    get_or_create_collection(business_key) -> Collection
    index_documents(docs, business_key) -> int          # returns chunk count
    clear_collection(business_key) -> None
"""

import hashlib
import logging
from pathlib import Path

import chromadb
from chromadb import Collection
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_chroma_client() -> chromadb.PersistentClient:
    """
    Return a persistent ChromaDB client using the directory from settings.
    The directory is created automatically if it does not exist.
    """
    persist_dir: Path = settings.chroma_persist_dir
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def _get_embedder() -> OpenAIEmbeddings:
    """Return an OpenAIEmbeddings instance using the configured model."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def _resolve_collection_name(business_key: str) -> str:
    """
    Map a short business key (e.g. 'cafe') to its full collection name
    (e.g. 'cafe_restaurant') as defined in config.yaml.

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
    """
    Generate a stable, unique ID for a chunk.

    The ID is a SHA-256 hash of the source path + position so that
    re-ingesting the same file produces the same IDs (upsert = no
    duplicates) while different files never collide.
    """
    source = doc.metadata.get("source", "unknown")
    raw = f"{source}::{position}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create_collection(business_key: str) -> Collection:
    """
    Return the ChromaDB collection for a business, creating it if needed.

    Args:
        business_key: Short key from config (e.g. 'cafe', 'hotel', 'gems').

    Returns:
        A ChromaDB Collection object.

    Raises:
        KeyError: If business_key is not in the configured collections.
    """
    collection_name = _resolve_collection_name(business_key)
    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for embeddings
    )
    logger.debug("Resolved collection '%s' for key '%s'",
                 collection_name, business_key)
    return collection


def index_documents(docs: list[Document], business_key: str) -> int:
    """
    Embed and upsert a list of Documents into the ChromaDB collection.

    Documents must already be split into chunks and each chunk must have a
    'chunk_id' key in its metadata (added by splitter.split_documents).

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

    collection = get_or_create_collection(business_key)
    embedder = _get_embedder()

    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]

    # Generate stable IDs based on source + position so re-ingestion is safe.
    ids = [_make_chunk_id(doc, i) for i, doc in enumerate(docs)]

    logger.info(
        "Embedding %d chunks for collection '%s'...", len(texts), business_key
    )
    vectors = embedder.embed_documents(texts)

    # upsert = insert if new, update if same id already exists
    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )

    logger.info("Indexed %d chunks into '%s'.", len(docs), business_key)
    return len(docs)


def clear_collection(business_key: str) -> None:
    """
    Delete and recreate the collection for the given business key.

    Use this before a full re-index to start from a clean state.

    Args:
        business_key: Short key from config (e.g. 'cafe', 'hotel', 'gems').

    Raises:
        KeyError: If business_key is not in the configured collections.
    """
    collection_name = _resolve_collection_name(business_key)
    client = _get_chroma_client()
    client.delete_collection(name=collection_name)
    client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("Cleared and recreated collection '%s'.", collection_name)
