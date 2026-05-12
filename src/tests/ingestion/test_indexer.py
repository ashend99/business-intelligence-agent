"""
tests/ingestion/test_indexer.py

Test suite for ingestion/indexer.py covering:

    _make_chunk_id()
    ├── Deterministic — same inputs always produce same ID
    ├── Unique — different source or position produces different ID
    └── Length — always 32 hex characters

    _resolve_collection_name()
    ├── Happy path — valid keys map to correct collection names
    └── Error case — unknown key raises KeyError

    get_collection_count()
    ├── Returns 0 for an empty collection
    └── Error case — unknown business key raises KeyError

    index_documents()
    ├── Happy path — returns correct count, calls upsert
    ├── Idempotent — indexing the same docs twice does not duplicate
    ├── Vectors are computed from document text
    └── Error cases — empty docs, unknown business key

    clear_collection()
    ├── Happy path — collection is emptied
    └── Error case — unknown business key

All OpenAI embedding calls are mocked to avoid real network traffic.
ChromaDB uses a PersistentClient in a temp directory via ChromaDBManager.
The factory get_vector_db() is patched to return this isolated manager.
"""

import hashlib
from unittest.mock import MagicMock

import chromadb
import pytest
from langchain_core.documents import Document

from ingestion.indexer import (
    _make_chunk_id,
    _resolve_collection_name,
    clear_collection,
    get_collection_count,
    index_documents,
)
from ingestion.vectordb import ChromaDBManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(content: str, source: str = "test.txt", chunk_id: int = 0) -> Document:
    return Document(
        page_content=content,
        metadata={"source": source, "chunk_id": chunk_id},
    )


def fake_vectors(texts: list[str]) -> list[list[float]]:
    """Return a deterministic unit vector for each text (avoids OpenAI calls)."""
    return [[0.1, 0.2, 0.3] for _ in texts]


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def chroma_manager(monkeypatch, tmp_path):
    """
    Build a ChromaDBManager backed by a PersistentClient in a unique temp
    directory, then patch get_vector_db() so that indexer.py uses it.
    Each test gets a completely isolated ChromaDB instance.
    """
    manager = ChromaDBManager.__new__(ChromaDBManager)
    manager._client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))

    monkeypatch.setattr("ingestion.indexer.get_vector_db", lambda: manager)
    return manager


@pytest.fixture()
def mock_embedder(monkeypatch):
    """Replace _get_embedder() with a mock that returns fake vectors."""
    embedder = MagicMock()
    embedder.embed_documents.side_effect = fake_vectors
    monkeypatch.setattr("ingestion.indexer._get_embedder", lambda: embedder)
    return embedder


# ===========================================================================
# _make_chunk_id()
# ===========================================================================

class TestMakeChunkId:

    def test_returns_32_hex_characters(self):
        doc = make_doc("hello", source="report.txt")
        result = _make_chunk_id(doc, 0)
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_is_deterministic(self):
        doc = make_doc("hello", source="report.txt")
        id1 = _make_chunk_id(doc, 0)
        id2 = _make_chunk_id(doc, 0)
        assert id1 == id2

    def test_different_position_produces_different_id(self):
        doc = make_doc("hello", source="report.txt")
        assert _make_chunk_id(doc, 0) != _make_chunk_id(doc, 1)

    def test_different_source_produces_different_id(self):
        doc_a = make_doc("hello", source="file_a.txt")
        doc_b = make_doc("hello", source="file_b.txt")
        assert _make_chunk_id(doc_a, 0) != _make_chunk_id(doc_b, 0)

    def test_missing_source_metadata_uses_unknown(self):
        doc = Document(page_content="text", metadata={})
        result = _make_chunk_id(doc, 0)
        expected_raw = "unknown::0"
        expected = hashlib.sha256(expected_raw.encode()).hexdigest()[:32]
        assert result == expected


# ===========================================================================
# _resolve_collection_name()
# ===========================================================================

class TestResolveCollectionName:

    def test_cafe_resolves_to_cafe_restaurant(self):
        assert _resolve_collection_name("cafe") == "cafe_restaurant"

    def test_hotel_resolves_to_airport_hotel(self):
        assert _resolve_collection_name("hotel") == "airport_hotel"

    def test_gems_resolves_to_gem_business(self):
        assert _resolve_collection_name("gems") == "gem_business"

    def test_unknown_key_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown business key"):
            _resolve_collection_name("nonexistent")

    def test_error_message_includes_valid_keys(self):
        with pytest.raises(KeyError, match="cafe"):
            _resolve_collection_name("invalid")


# ===========================================================================
# get_collection_count()
# ===========================================================================

class TestGetCollectionCount:

    def test_returns_zero_for_empty_collection(self, chroma_manager):
        count = get_collection_count("cafe")
        assert count == 0

    def test_unknown_key_raises_key_error(self, chroma_manager):
        with pytest.raises(KeyError):
            get_collection_count("unknown_business")

    def test_hotel_and_gems_available(self, chroma_manager):
        assert get_collection_count("hotel") == 0
        assert get_collection_count("gems") == 0


# ===========================================================================
# index_documents()
# ===========================================================================

class TestIndexDocuments:

    def test_returns_correct_chunk_count(self, chroma_manager, mock_embedder):
        docs = [make_doc(f"chunk {i}", chunk_id=i) for i in range(5)]
        result = index_documents(docs, "cafe")
        assert result == 5

    def test_embed_documents_called_with_correct_texts(self, chroma_manager, mock_embedder):
        docs = [make_doc("text one", chunk_id=0), make_doc("text two", chunk_id=1)]
        index_documents(docs, "cafe")
        mock_embedder.embed_documents.assert_called_once_with(
            ["text one", "text two"]
        )

    def test_chunks_are_stored_in_collection(self, chroma_manager, mock_embedder):
        docs = [make_doc(f"content {i}", source="sales.txt", chunk_id=i) for i in range(3)]
        index_documents(docs, "cafe")
        assert get_collection_count("cafe") == 3

    def test_metadata_is_preserved_in_collection(self, chroma_manager, mock_embedder):
        doc = make_doc("important data", source="hotel_report.txt", chunk_id=0)
        index_documents([doc], "hotel")
        col = chroma_manager._client.get_collection("airport_hotel")
        result = col.get(include=["metadatas"])
        assert result["metadatas"][0]["source"] == "hotel_report.txt"

    def test_is_idempotent_on_same_documents(self, chroma_manager, mock_embedder):
        docs = [make_doc(f"chunk {i}", source="gems.txt", chunk_id=i) for i in range(4)]
        index_documents(docs, "gems")
        index_documents(docs, "gems")  # index again — should not duplicate
        assert get_collection_count("gems") == 4  # still 4, not 8

    def test_different_sources_accumulate_correctly(self, chroma_manager, mock_embedder):
        docs_a = [make_doc(f"doc_a chunk {i}", source="file_a.txt", chunk_id=i) for i in range(2)]
        docs_b = [make_doc(f"doc_b chunk {i}", source="file_b.txt", chunk_id=i) for i in range(3)]
        index_documents(docs_a, "cafe")
        index_documents(docs_b, "cafe")
        assert get_collection_count("cafe") == 5

    def test_empty_docs_raises_value_error(self, chroma_manager, mock_embedder):
        with pytest.raises(ValueError, match="docs must not be empty"):
            index_documents([], "cafe")

    def test_unknown_business_key_raises_key_error(self, chroma_manager, mock_embedder):
        docs = [make_doc("some text")]
        with pytest.raises(KeyError):
            index_documents(docs, "unknown_key")


# ===========================================================================
# clear_collection()
# ===========================================================================

class TestClearCollection:

    def test_collection_is_empty_after_clear(self, chroma_manager, mock_embedder):
        docs = [make_doc(f"chunk {i}", chunk_id=i) for i in range(5)]
        index_documents(docs, "cafe")
        assert get_collection_count("cafe") == 5

        clear_collection("cafe")

        assert get_collection_count("cafe") == 0

    def test_can_index_after_clear(self, chroma_manager, mock_embedder):
        docs = [make_doc(f"chunk {i}", chunk_id=i) for i in range(3)]
        index_documents(docs, "hotel")
        clear_collection("hotel")
        new_docs = [make_doc("fresh data", chunk_id=0)]
        index_documents(new_docs, "hotel")
        assert get_collection_count("hotel") == 1

    def test_unknown_key_raises_key_error(self, chroma_manager):
        with pytest.raises(KeyError):
            clear_collection("nonexistent")
