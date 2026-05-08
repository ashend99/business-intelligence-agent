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

    get_or_create_collection()
    ├── Returns a ChromaDB Collection object
    ├── Creates collection if it does not exist
    └── Error case — unknown business key

    index_documents()
    ├── Happy path — returns correct count, calls upsert
    ├── Idempotent — indexing the same docs twice does not duplicate
    ├── Vectors are computed from document text
    └── Error cases — empty docs, unknown business key

    clear_collection()
    ├── Happy path — collection is emptied
    └── Error case — unknown business key

All OpenAI embedding calls are mocked to avoid real network traffic.
ChromaDB uses an in-memory client (not PersistentClient) in all tests.
"""

import hashlib
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from langchain_core.documents import Document

from ingestion.indexer import (
    _make_chunk_id,
    _resolve_collection_name,
    clear_collection,
    get_or_create_collection,
    index_documents,
)


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
# Shared fixture: in-memory ChromaDB + mocked embedder
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_chroma(monkeypatch, tmp_path):
    """
    Replace _get_chroma_client() with a PersistentClient in a unique temp
    directory so each test gets a completely isolated ChromaDB instance.
    EphemeralClient has global in-process state and leaks between tests.
    """
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))

    monkeypatch.setattr("ingestion.indexer._get_chroma_client", lambda: client)
    return client


@pytest.fixture()
def mock_embedder(monkeypatch):
    """
    Replace _get_embedder() with a mock that returns fake vectors.
    This avoids real OpenAI API calls.
    """
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
# get_or_create_collection()
# ===========================================================================

class TestGetOrCreateCollection:

    def test_returns_collection_object(self, mock_chroma):
        col = get_or_create_collection("cafe")
        assert col is not None
        assert hasattr(col, "upsert")

    def test_collection_name_matches_config(self, mock_chroma):
        col = get_or_create_collection("cafe")
        assert col.name == "cafe_restaurant"

    def test_hotel_collection_name(self, mock_chroma):
        col = get_or_create_collection("hotel")
        assert col.name == "airport_hotel"

    def test_gems_collection_name(self, mock_chroma):
        col = get_or_create_collection("gems")
        assert col.name == "gem_business"

    def test_calling_twice_returns_same_collection(self, mock_chroma):
        col1 = get_or_create_collection("cafe")
        col2 = get_or_create_collection("cafe")
        assert col1.name == col2.name

    def test_unknown_key_raises_key_error(self, mock_chroma):
        with pytest.raises(KeyError):
            get_or_create_collection("unknown_business")


# ===========================================================================
# index_documents()
# ===========================================================================

class TestIndexDocuments:

    def test_returns_correct_chunk_count(self, mock_chroma, mock_embedder):
        docs = [make_doc(f"chunk {i}", chunk_id=i) for i in range(5)]
        result = index_documents(docs, "cafe")
        assert result == 5

    def test_embed_documents_called_with_correct_texts(self, mock_chroma, mock_embedder):
        docs = [make_doc("text one", chunk_id=0), make_doc("text two", chunk_id=1)]
        index_documents(docs, "cafe")
        mock_embedder.embed_documents.assert_called_once_with(
            ["text one", "text two"]
        )

    def test_chunks_are_stored_in_collection(self, mock_chroma, mock_embedder):
        docs = [make_doc(f"content {i}", source="sales.txt", chunk_id=i) for i in range(3)]
        index_documents(docs, "cafe")
        col = mock_chroma.get_collection("cafe_restaurant")
        assert col.count() == 3

    def test_metadata_is_preserved_in_collection(self, mock_chroma, mock_embedder):
        doc = make_doc("important data", source="hotel_report.txt", chunk_id=0)
        index_documents([doc], "hotel")
        col = mock_chroma.get_collection("airport_hotel")
        result = col.get(include=["metadatas"])
        assert result["metadatas"][0]["source"] == "hotel_report.txt"

    def test_is_idempotent_on_same_documents(self, mock_chroma, mock_embedder):
        docs = [make_doc(f"chunk {i}", source="gems.txt", chunk_id=i) for i in range(4)]
        index_documents(docs, "gems")
        index_documents(docs, "gems")  # index again — should not duplicate
        col = mock_chroma.get_collection("gem_business")
        assert col.count() == 4  # still 4, not 8

    def test_different_sources_accumulate_correctly(self, mock_chroma, mock_embedder):
        docs_a = [make_doc(f"doc_a chunk {i}", source="file_a.txt", chunk_id=i) for i in range(2)]
        docs_b = [make_doc(f"doc_b chunk {i}", source="file_b.txt", chunk_id=i) for i in range(3)]
        index_documents(docs_a, "cafe")
        index_documents(docs_b, "cafe")
        col = mock_chroma.get_collection("cafe_restaurant")
        assert col.count() == 5

    def test_empty_docs_raises_value_error(self, mock_chroma, mock_embedder):
        with pytest.raises(ValueError, match="docs must not be empty"):
            index_documents([], "cafe")

    def test_unknown_business_key_raises_key_error(self, mock_chroma, mock_embedder):
        docs = [make_doc("some text")]
        with pytest.raises(KeyError):
            index_documents(docs, "unknown_key")


# ===========================================================================
# clear_collection()
# ===========================================================================

class TestClearCollection:

    def test_collection_is_empty_after_clear(self, mock_chroma, mock_embedder):
        docs = [make_doc(f"chunk {i}", chunk_id=i) for i in range(5)]
        index_documents(docs, "cafe")
        col = mock_chroma.get_collection("cafe_restaurant")
        assert col.count() == 5

        clear_collection("cafe")

        col = mock_chroma.get_collection("cafe_restaurant")
        assert col.count() == 0

    def test_can_index_after_clear(self, mock_chroma, mock_embedder):
        docs = [make_doc(f"chunk {i}", chunk_id=i) for i in range(3)]
        index_documents(docs, "hotel")
        clear_collection("hotel")
        new_docs = [make_doc("fresh data", chunk_id=0)]
        index_documents(new_docs, "hotel")
        col = mock_chroma.get_collection("airport_hotel")
        assert col.count() == 1

    def test_unknown_key_raises_key_error(self, mock_chroma):
        with pytest.raises(KeyError):
            clear_collection("nonexistent")
