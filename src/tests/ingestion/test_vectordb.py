"""
tests/ingestion/test_vectordb.py

Test suite for src/ingestion/vectordb.py covering all 10 required operations:

    VDB lifecycle
    ├── create_db()    — initialises ChromaDB client; idempotent
    └── delete_db()    — removes persist directory; client reset to None

    Collection lifecycle
    ├── ensure_collection()   — creates if missing; idempotent
    ├── delete_collection()   — removes without recreating
    └── clear_collection()    — wipes and recreates

    Document writes
    ├── upsert()              — inserts documents; stamps indexed_at metadata
    ├── upsert() update       — same id replaces previous document
    └── delete_documents()    — removes specific ids

    Document reads
    ├── count()               — returns count for one collection
    └── count_all()           — returns per-collection dict

    Maintenance
    └── delete_old_documents()— prunes by retention_days via indexed_at

    Factory
    └── get_vector_db()       — returns ChromaDBManager for provider "chroma"
                              — raises ValueError for unknown provider

All tests use an isolated ChromaDBManager whose _client is a PersistentClient
in a per-test tmp_path directory (no shared global state between tests).
Settings are monkeypatched so the real persist directory is never touched.
"""

import shutil
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import chromadb
import pytest

from ingestion.vectordb import ChromaDBManager, VectorDBManager, get_vector_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager(tmp_path, monkeypatch):
    """Isolated ChromaDBManager pointing at a temp directory."""
    persist_dir = tmp_path / "chroma"
    monkeypatch.setattr("ingestion.vectordb.settings.chroma_persist_dir", persist_dir)

    mgr = ChromaDBManager()
    mgr.create_db()
    return mgr


COLLECTION = "test_collection"
COLLECTION_B = "test_collection_b"

_FAKE_EMBEDDING = [0.1, 0.2, 0.3]
_FAKE_EMBEDDINGS = [[0.1, 0.2, 0.3]]


def _seed(manager: ChromaDBManager, collection: str = COLLECTION, n: int = 3):
    """Insert n documents into the collection and return their ids."""
    ids = [f"id_{i}" for i in range(n)]
    manager.upsert(
        collection_name=collection,
        ids=ids,
        embeddings=[_FAKE_EMBEDDING for _ in range(n)],
        documents=[f"doc {i}" for i in range(n)],
        metadatas=[{"source": f"file_{i}.txt"} for i in range(n)],
    )
    return ids


# ===========================================================================
# 1. create_db()
# ===========================================================================

class TestCreateDb:

    def test_client_is_initialised(self, tmp_path, monkeypatch):
        persist_dir = tmp_path / "chroma"
        monkeypatch.setattr("ingestion.vectordb.settings.chroma_persist_dir", persist_dir)

        mgr = ChromaDBManager()
        assert mgr._client is None

        mgr.create_db()
        assert mgr._client is not None

    def test_persist_directory_is_created(self, tmp_path, monkeypatch):
        persist_dir = tmp_path / "new_dir"
        monkeypatch.setattr("ingestion.vectordb.settings.chroma_persist_dir", persist_dir)

        mgr = ChromaDBManager()
        mgr.create_db()
        assert persist_dir.exists()

    def test_idempotent_does_not_raise(self, manager):
        manager.create_db()  # second call must not raise
        assert manager._client is not None


# ===========================================================================
# 2. delete_db()
# ===========================================================================

class TestDeleteDb:

    def test_persist_directory_is_removed(self, manager, tmp_path):
        persist_dir = tmp_path / "chroma"
        assert persist_dir.exists()

        manager.delete_db()
        assert not persist_dir.exists()

    def test_client_is_reset_to_none(self, manager):
        manager.delete_db()
        assert manager._client is None

    def test_delete_on_nonexistent_dir_does_not_raise(self, tmp_path, monkeypatch):
        persist_dir = tmp_path / "missing"
        monkeypatch.setattr("ingestion.vectordb.settings.chroma_persist_dir", persist_dir)
        mgr = ChromaDBManager()
        mgr.delete_db()  # directory never existed — should not raise


# ===========================================================================
# 3. ensure_collection()
# ===========================================================================

class TestEnsureCollection:

    def test_collection_is_created(self, manager):
        manager.ensure_collection(COLLECTION)
        names = [c.name for c in manager._db.list_collections()]
        assert COLLECTION in names

    def test_idempotent_calling_twice_does_not_raise(self, manager):
        manager.ensure_collection(COLLECTION)
        manager.ensure_collection(COLLECTION)
        names = [c.name for c in manager._db.list_collections()]
        assert names.count(COLLECTION) == 1


# ===========================================================================
# 4. delete_collection()
# ===========================================================================

class TestDeleteCollection:

    def test_collection_is_removed(self, manager):
        manager.ensure_collection(COLLECTION)
        manager.delete_collection(COLLECTION)
        names = [c.name for c in manager._db.list_collections()]
        assert COLLECTION not in names

    def test_other_collections_are_unaffected(self, manager):
        manager.ensure_collection(COLLECTION)
        manager.ensure_collection(COLLECTION_B)
        manager.delete_collection(COLLECTION)
        names = [c.name for c in manager._db.list_collections()]
        assert COLLECTION_B in names

    def test_delete_nonexistent_raises(self, manager):
        with pytest.raises(Exception):
            manager.delete_collection("does_not_exist")


# ===========================================================================
# 4b. clear_collection()
# ===========================================================================

class TestClearCollection:

    def test_documents_are_removed(self, manager):
        _seed(manager)
        assert manager.count(COLLECTION) == 3

        manager.clear_collection(COLLECTION)
        assert manager.count(COLLECTION) == 0

    def test_collection_still_exists_after_clear(self, manager):
        manager.ensure_collection(COLLECTION)
        manager.clear_collection(COLLECTION)
        names = [c.name for c in manager._db.list_collections()]
        assert COLLECTION in names

    def test_can_upsert_after_clear(self, manager):
        _seed(manager)
        manager.clear_collection(COLLECTION)
        _seed(manager, n=2)
        assert manager.count(COLLECTION) == 2


# ===========================================================================
# 5. upsert() — add documents
# ===========================================================================

class TestUpsertAdd:

    def test_documents_are_stored(self, manager):
        _seed(manager, n=4)
        assert manager.count(COLLECTION) == 4

    def test_indexed_at_is_stamped_in_metadata(self, manager):
        manager.upsert(
            collection_name=COLLECTION,
            ids=["doc_1"],
            embeddings=[_FAKE_EMBEDDING],
            documents=["hello world"],
            metadatas=[{"source": "test.txt"}],
        )
        col = manager._db.get_collection(COLLECTION)
        result = col.get(ids=["doc_1"], include=["metadatas"])
        meta = result["metadatas"][0]
        assert "indexed_at" in meta
        # Must be a valid ISO-8601 string
        datetime.fromisoformat(meta["indexed_at"])

    def test_original_metadata_is_preserved(self, manager):
        manager.upsert(
            collection_name=COLLECTION,
            ids=["doc_1"],
            embeddings=[_FAKE_EMBEDDING],
            documents=["content"],
            metadatas=[{"source": "report.pdf", "page": 3}],
        )
        col = manager._db.get_collection(COLLECTION)
        result = col.get(ids=["doc_1"], include=["metadatas"])
        meta = result["metadatas"][0]
        assert meta["source"] == "report.pdf"
        assert meta["page"] == 3


# ===========================================================================
# 6. upsert() — update (same id replaces previous)
# ===========================================================================

class TestUpsertUpdate:

    def test_same_id_replaces_document(self, manager):
        manager.upsert(
            collection_name=COLLECTION,
            ids=["doc_1"],
            embeddings=[_FAKE_EMBEDDING],
            documents=["original content"],
            metadatas=[{"version": 1}],
        )
        manager.upsert(
            collection_name=COLLECTION,
            ids=["doc_1"],
            embeddings=[_FAKE_EMBEDDING],
            documents=["updated content"],
            metadatas=[{"version": 2}],
        )
        # Count must still be 1 — no duplicate
        assert manager.count(COLLECTION) == 1

        col = manager._db.get_collection(COLLECTION)
        result = col.get(ids=["doc_1"], include=["documents", "metadatas"])
        assert result["documents"][0] == "updated content"
        assert result["metadatas"][0]["version"] == 2

    def test_updating_subset_does_not_affect_others(self, manager):
        _seed(manager, n=3)
        manager.upsert(
            collection_name=COLLECTION,
            ids=["id_0"],
            embeddings=[_FAKE_EMBEDDING],
            documents=["replaced"],
            metadatas=[{"source": "new.txt"}],
        )
        assert manager.count(COLLECTION) == 3


# ===========================================================================
# 7. delete_documents()
# ===========================================================================

class TestDeleteDocuments:

    def test_specified_ids_are_removed(self, manager):
        ids = _seed(manager, n=5)
        manager.delete_documents(COLLECTION, ids=["id_0", "id_2"])
        assert manager.count(COLLECTION) == 3

    def test_remaining_ids_are_intact(self, manager):
        _seed(manager, n=3)
        manager.delete_documents(COLLECTION, ids=["id_0"])
        col = manager._db.get_collection(COLLECTION)
        remaining = col.get(include=["metadatas"])["ids"]
        assert "id_0" not in remaining
        assert "id_1" in remaining
        assert "id_2" in remaining

    def test_delete_all_ids_empties_collection(self, manager):
        ids = _seed(manager, n=3)
        manager.delete_documents(COLLECTION, ids=ids)
        assert manager.count(COLLECTION) == 0


# ===========================================================================
# 8. count() — single collection
# ===========================================================================

class TestCount:

    def test_empty_collection_returns_zero(self, manager):
        manager.ensure_collection(COLLECTION)
        assert manager.count(COLLECTION) == 0

    def test_returns_correct_count_after_upsert(self, manager):
        _seed(manager, n=7)
        assert manager.count(COLLECTION) == 7

    def test_counts_are_independent_per_collection(self, manager):
        _seed(manager, COLLECTION, n=3)
        _seed(manager, COLLECTION_B, n=5)
        assert manager.count(COLLECTION) == 3
        assert manager.count(COLLECTION_B) == 5


# ===========================================================================
# 9. count_all() — all collections
# ===========================================================================

class TestCountAll:

    def test_returns_empty_dict_when_no_collections(self, manager):
        result = manager.count_all()
        assert result == {}

    def test_returns_count_for_each_collection(self, manager):
        _seed(manager, COLLECTION, n=4)
        _seed(manager, COLLECTION_B, n=2)
        result = manager.count_all()
        assert result[COLLECTION] == 4
        assert result[COLLECTION_B] == 2

    def test_result_is_dict_of_str_to_int(self, manager):
        _seed(manager, COLLECTION, n=1)
        result = manager.count_all()
        assert isinstance(result, dict)
        for k, v in result.items():
            assert isinstance(k, str)
            assert isinstance(v, int)


# ===========================================================================
# 10. delete_old_documents()
# ===========================================================================

class TestDeleteOldDocuments:

    def _insert_with_timestamp(
        self,
        manager: ChromaDBManager,
        doc_id: str,
        indexed_at: datetime,
        collection: str = COLLECTION,
    ) -> None:
        """Insert a single document with a manually set indexed_at timestamp."""
        col = manager._db.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}
        )
        col.upsert(
            ids=[doc_id],
            embeddings=[_FAKE_EMBEDDING],
            documents=[f"content of {doc_id}"],
            metadatas=[{"indexed_at": indexed_at.isoformat(), "source": "test.txt"}],
        )

    def test_old_documents_are_deleted(self, manager):
        now = datetime.now(tz=timezone.utc)
        self._insert_with_timestamp(manager, "old_doc", now - timedelta(days=40))
        self._insert_with_timestamp(manager, "new_doc", now - timedelta(days=5))

        deleted = manager.delete_old_documents(COLLECTION, retention_days=30)

        assert deleted == 1
        assert manager.count(COLLECTION) == 1

    def test_recent_documents_are_kept(self, manager):
        now = datetime.now(tz=timezone.utc)
        self._insert_with_timestamp(manager, "doc_a", now - timedelta(days=10))
        self._insert_with_timestamp(manager, "doc_b", now - timedelta(days=20))

        deleted = manager.delete_old_documents(COLLECTION, retention_days=30)

        assert deleted == 0
        assert manager.count(COLLECTION) == 2

    def test_returns_correct_deleted_count(self, manager):
        now = datetime.now(tz=timezone.utc)
        for i in range(5):
            self._insert_with_timestamp(
                manager, f"old_{i}", now - timedelta(days=60 + i)
            )
        for i in range(3):
            self._insert_with_timestamp(
                manager, f"new_{i}", now - timedelta(days=1)
            )

        deleted = manager.delete_old_documents(COLLECTION, retention_days=30)
        assert deleted == 5
        assert manager.count(COLLECTION) == 3

    def test_documents_without_indexed_at_are_skipped(self, manager):
        col = manager._db.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        col.upsert(
            ids=["no_timestamp"],
            embeddings=[_FAKE_EMBEDDING],
            documents=["no timestamp doc"],
            metadatas=[{"source": "mystery.txt"}],
        )
        deleted = manager.delete_old_documents(COLLECTION, retention_days=0)
        assert deleted == 0

    def test_boundary_exactly_at_retention_is_deleted(self, manager):
        now = datetime.now(tz=timezone.utc)
        # Slightly older than the boundary (1 second over)
        self._insert_with_timestamp(
            manager, "boundary_doc", now - timedelta(days=30, seconds=1)
        )
        deleted = manager.delete_old_documents(COLLECTION, retention_days=30)
        assert deleted == 1


# ===========================================================================
# Factory — get_vector_db()
# ===========================================================================

class TestGetVectorDb:

    def test_returns_chroma_manager_for_chroma_provider(self, monkeypatch):
        monkeypatch.setattr(
            "ingestion.vectordb.settings.vectorstore_provider", "chroma"
        )
        db = get_vector_db()
        assert isinstance(db, ChromaDBManager)

    def test_unknown_provider_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(
            "ingestion.vectordb.settings.vectorstore_provider", "pinecone"
        )
        with pytest.raises(ValueError, match="Unknown vectorstore provider"):
            get_vector_db()

    def test_error_message_lists_valid_providers(self, monkeypatch):
        monkeypatch.setattr(
            "ingestion.vectordb.settings.vectorstore_provider", "unknown"
        )
        with pytest.raises(ValueError, match="chroma"):
            get_vector_db()
