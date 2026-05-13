"""Vector database abstraction layer.

Contains:
  - VectorDBManager  — abstract base class all providers must implement
  - ChromaDBManager  — ChromaDB (local persistent) implementation
  - get_vector_db()  — factory that returns the configured provider

To add a new provider:
  1. Subclass VectorDBManager and implement all abstract methods below.
  2. Add an entry to _REGISTRY mapping the provider name to the class.
  3. Set vectorstore.provider: "<provider>" in config.yaml.

Supported operations
--------------------
VDB lifecycle      : create_db(), delete_db()
Collection lifecycle: ensure_collection(), delete_collection(), clear_collection()
Document writes    : upsert(), delete_documents()
Document reads     : count(), count_all(), query()
Maintenance        : delete_old_documents()
"""

import logging
import gc
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from config.settings import settings

logger = logging.getLogger(__name__)


# ===========================================================================
# Abstract base
# ===========================================================================

class VectorDBManager(ABC):
    """Provider-agnostic interface for vector store operations.

    Method groups
    -------------
    VDB lifecycle       — create_db, delete_db
    Collection lifecycle— ensure_collection, delete_collection, clear_collection
    Document writes     — upsert, delete_documents
    Document reads      — count, count_all, query
    Maintenance         — delete_old_documents

    The `upsert` method stamps every document with an ``indexed_at`` ISO-8601
    UTC timestamp in its metadata so that ``delete_old_documents`` can filter
    by age without any external tracking.
    """

    # ------------------------------------------------------------------
    # 1 & 2 — VDB lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def create_db(self) -> None:
        """Initialise and connect to the vector database.

        Implementations should be idempotent — calling this when the DB
        already exists must not raise or destroy data.
        """

    @abstractmethod
    def delete_db(self) -> None:
        """Permanently destroy the entire vector database and all its data.

        WARNING: irreversible. All collections and documents are lost.
        """

    # ------------------------------------------------------------------
    # 3 & 4 — Collection lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def ensure_collection(self, collection_name: str) -> None:
        """Create the collection if it does not already exist (idempotent).

        Args:
            collection_name: Name of the collection to create or verify.
        """

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Permanently delete a collection and all its documents.

        Unlike ``clear_collection`` the collection is NOT recreated.

        Args:
            collection_name: Name of the collection to remove.
        """

    @abstractmethod
    def clear_collection(self, collection_name: str) -> None:
        """Delete and immediately recreate a collection (wipe all documents).

        Use this before a full re-index to start from a clean state while
        keeping the collection available.

        Args:
            collection_name: Name of the collection to wipe.
        """

    # ------------------------------------------------------------------
    # 5, 6 & 7 — Document writes
    # ------------------------------------------------------------------

    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Insert or replace vectors in the collection.

        Documents sharing the same ``id`` fully replace the previous entry,
        satisfying requirement 6 (update = upsert with same id).

        An ``indexed_at`` UTC timestamp is automatically injected into every
        metadata dict so that ``delete_old_documents`` can filter by age.

        Args:
            collection_name: Target collection.
            ids:             Stable unique IDs, one per document.
            embeddings:      Dense float vectors, one per document.
            documents:       Raw text content, one per document.
            metadatas:       Arbitrary metadata dicts, one per document.
        """

    @abstractmethod
    def delete_documents(self, collection_name: str, ids: list[str]) -> None:
        """Remove specific documents from a collection by their IDs.

        Args:
            collection_name: Collection containing the documents.
            ids:             List of document IDs to delete.
        """

    # ------------------------------------------------------------------
    # 8 & 9 — Document reads
    # ------------------------------------------------------------------

    @abstractmethod
    def count(self, collection_name: str) -> int:
        """Return the number of vectors in a single collection.

        Args:
            collection_name: The collection to count.

        Returns:
            Total number of indexed vectors.
        """

    @abstractmethod
    def count_all(self) -> dict[str, int]:
        """Return a per-collection document count for every collection.

        Returns:
            Dict mapping collection_name → document count.
        """

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int,
    ) -> dict:
        """Retrieve the nearest neighbours for a query vector.

        Args:
            collection_name: Collection to search.
            query_embedding: Dense float vector for the query.
            n_results:       Maximum number of results to return.

        Returns:
            A dict with at least the keys:
                "documents"  : list[list[str]]   — text of each result
                "metadatas"  : list[list[dict]]  — metadata of each result
                "distances"  : list[list[float]] — similarity scores
        """

    # ------------------------------------------------------------------
    # 10 — Maintenance
    # ------------------------------------------------------------------

    @abstractmethod
    def delete_old_documents(
        self, collection_name: str, retention_days: int
    ) -> int:
        """Delete documents older than ``retention_days`` from a collection.

        Requires that documents were indexed via ``upsert`` (which stamps
        an ``indexed_at`` ISO-8601 UTC timestamp in metadata).

        Args:
            collection_name: Collection to prune.
            retention_days:  Documents indexed more than this many days ago
                             are deleted.

        Returns:
            Number of documents deleted.
        """


# ===========================================================================
# ChromaDB implementation
# ===========================================================================

_CHROMA_COLLECTION_METADATA = {"hnsw:space": "cosine"}


class ChromaDBManager(VectorDBManager):
    """VectorDBManager backed by a local persistent ChromaDB instance."""

    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @property
    def _db(self) -> chromadb.PersistentClient:
        """Return (or lazily create) the shared ChromaDB client."""
        if self._client is None:
            self.create_db()
        return self._client  # type: ignore[return-value]

    def _get_collection(self, collection_name: str) -> chromadb.Collection:
        return self._db.get_or_create_collection(
            name=collection_name,
            metadata=_CHROMA_COLLECTION_METADATA,
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 1 & 2 — VDB lifecycle
    # ------------------------------------------------------------------

    def create_db(self) -> None:
        persist_dir: Path = settings.chroma_persist_dir
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        logger.info("ChromaDB initialised at %s", persist_dir)

    def delete_db(self) -> None:
        """Delete the entire ChromaDB persist directory."""
        persist_dir: Path = settings.chroma_persist_dir
        if self._client is not None:
            # Stop the internal system to release the SQLite file lock
            try:
                self._client._system.stop()
            except Exception:
                pass
            self._client = None
            # Force GC to flush remaining SQLite handles (required on Windows)
            gc.collect()
        if persist_dir.exists():
            shutil.rmtree(persist_dir)
            logger.warning("ChromaDB deleted: %s", persist_dir)

    # ------------------------------------------------------------------
    # 3 & 4 — Collection lifecycle
    # ------------------------------------------------------------------

    def ensure_collection(self, collection_name: str) -> None:
        self._get_collection(collection_name)
        logger.debug("Ensured collection '%s' exists.", collection_name)

    def delete_collection(self, collection_name: str) -> None:
        self._db.delete_collection(name=collection_name)
        logger.info("Deleted collection '%s'.", collection_name)

    def clear_collection(self, collection_name: str) -> None:
        self._db.delete_collection(name=collection_name)
        self._db.create_collection(
            name=collection_name,
            metadata=_CHROMA_COLLECTION_METADATA,
        )
        logger.info("Cleared and recreated collection '%s'.", collection_name)

    # ------------------------------------------------------------------
    # 5, 6 & 7 — Document writes
    # ------------------------------------------------------------------

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        # Stamp each document with the current UTC time for retention pruning
        now = self._now_iso()
        stamped = [{**m, "indexed_at": now} for m in metadatas]

        self._get_collection(collection_name).upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=stamped,
        )
        logger.debug("Upserted %d vectors into '%s'.", len(ids), collection_name)

    def delete_documents(self, collection_name: str, ids: list[str]) -> None:
        self._get_collection(collection_name).delete(ids=ids)
        logger.info(
            "Deleted %d document(s) from '%s'.", len(ids), collection_name
        )

    # ------------------------------------------------------------------
    # 8 & 9 — Document reads
    # ------------------------------------------------------------------

    def count(self, collection_name: str) -> int:
        return self._get_collection(collection_name).count()

    def count_all(self) -> dict[str, int]:
        collections = self._db.list_collections()
        return {col.name: col.count() for col in collections}

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int,
    ) -> dict:
        return self._get_collection(collection_name).query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    # ------------------------------------------------------------------
    # 10 — Maintenance
    # ------------------------------------------------------------------

    def delete_old_documents(
        self, collection_name: str, retention_days: int
    ) -> int:
        collection = self._get_collection(collection_name)
        all_docs = collection.get(include=["metadatas"])
        ids_to_delete: list[str] = []
        cutoff = datetime.now(tz=timezone.utc).timestamp() - retention_days * 86400

        for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
            indexed_at_str: str | None = (meta or {}).get("indexed_at")
            if not indexed_at_str:
                continue
            try:
                indexed_ts = datetime.fromisoformat(indexed_at_str).timestamp()
            except ValueError:
                continue
            if indexed_ts < cutoff:
                ids_to_delete.append(doc_id)

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(
                "Pruned %d document(s) older than %d day(s) from '%s'.",
                len(ids_to_delete),
                retention_days,
                collection_name,
            )
        return len(ids_to_delete)


# ===========================================================================
# Factory
# ===========================================================================

# Maps provider name (config value) → (module_path, class_name).
# Add new providers here — no other file needs to change.
_REGISTRY: dict[str, type[VectorDBManager]] = {
    "chroma": ChromaDBManager,
}


def get_vector_db() -> VectorDBManager:
    """Return a VectorDBManager instance for the configured provider.

    Reads vectorstore.provider from settings. Raises ValueError if the
    provider is not registered.

    Returns:
        A concrete VectorDBManager instance.

    Raises:
        ValueError: If the provider is unknown.
    """
    provider = settings.vectorstore_provider
    cls = _REGISTRY.get(provider)

    if cls is None:
        valid = list(_REGISTRY.keys())
        raise ValueError(
            f"Unknown vectorstore provider '{provider}'. "
            f"Valid options: {valid}. "
            f"Update vectorstore.provider in config.yaml."
        )

    return cls()
