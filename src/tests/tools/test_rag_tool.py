"""
tests/tools/test_rag_tool.py

Test suite for tools/rag_tool.py covering:

    _resolve_collection_name()
    ├── Valid keys map to correct collection names
    └── Unknown key raises KeyError

    _format_results()
    ├── Happy path — numbered list with source citations
    ├── Empty input → "No relevant documents found."
    └── Missing source metadata falls back to "unknown source"

    _rerank()
    ├── Returns top_k results
    ├── Output length is capped at top_k
    ├── Returns correct structure (docs, metas)
    └── Fewer candidates than top_k returns all

    build_rag_tool()
    ├── Returns a callable LangChain tool
    ├── Tool has the correct name
    └── Unknown business key raises KeyError at build time

    search_documents() — the tool's __call__
    ├── Happy path — returns formatted string with source citations
    ├── Reranker is skipped when candidates <= top_k
    ├── Reranker is called when candidates > top_k
    ├── Collection not found → returns "no documents" message
    └── Empty collection → returns "no documents" message

All external I/O is mocked:
  - OpenAI embed_query   → monkeypatched
  - ChromaDB client      → monkeypatched with PersistentClient in tmp_path
  - FlashRank Ranker     → monkeypatched to avoid model download in CI
"""

from unittest.mock import MagicMock, patch

import chromadb
import pytest
from langchain_core.tools import BaseTool

from tools.rag_tool import (
    RERANK_FETCH_MULTIPLIER,
    _format_results,
    _rerank,
    _resolve_collection_name,
    build_rag_tool,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_chroma(monkeypatch, tmp_path):
    """Isolated PersistentClient per test — no shared ChromaDB state."""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    monkeypatch.setattr("tools.rag_tool._get_chroma_client", lambda: client)
    return client


@pytest.fixture()
def mock_embedder(monkeypatch):
    """Mock OpenAI embedder — returns a fixed vector for any query."""
    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1, 0.2, 0.3]
    monkeypatch.setattr("tools.rag_tool._get_embedder", lambda: embedder)
    return embedder


@pytest.fixture()
def mock_reranker(monkeypatch):
    """
    Mock FlashRank Ranker so tests never download the model.
    The mock returns passages in reverse order (simulating a rerank that
    flips the order) so tests can verify reranking actually ran.
    """
    def fake_rerank(request):
        # Return passages in reversed order with fake scores
        return [
            {"text": p["text"], "meta": p["meta"], "score": 1.0 - (i * 0.1)}
            for i, p in enumerate(reversed(request.passages))
        ]

    ranker = MagicMock()
    ranker.rerank.side_effect = fake_rerank
    monkeypatch.setattr("tools.rag_tool.Ranker", lambda: ranker)
    return ranker


def seed_collection(client: chromadb.PersistentClient, name: str, n: int) -> None:
    """
    Create and populate a ChromaDB collection with n fake chunks.
    Uses fixed 3-dim vectors so no real embeddings are needed.
    """
    col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    col.upsert(
        ids=[f"id_{i}" for i in range(n)],
        embeddings=[[0.1 + i * 0.01, 0.2, 0.3] for i in range(n)],
        documents=[f"Chunk {i}: some business content about topic {i}." for i in range(n)],
        metadatas=[{"source": f"report_{i}.txt", "chunk_id": i} for i in range(n)],
    )


# ===========================================================================
# _resolve_collection_name()
# ===========================================================================

class TestResolveCollectionName:

    def test_cafe_resolves_correctly(self):
        assert _resolve_collection_name("cafe") == "cafe_restaurant"

    def test_hotel_resolves_correctly(self):
        assert _resolve_collection_name("hotel") == "airport_hotel"

    def test_gems_resolves_correctly(self):
        assert _resolve_collection_name("gems") == "gem_business"

    def test_unknown_key_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown business key"):
            _resolve_collection_name("bakery")

    def test_error_includes_valid_keys(self):
        with pytest.raises(KeyError, match="cafe"):
            _resolve_collection_name("invalid")


# ===========================================================================
# _format_results()
# ===========================================================================

class TestFormatResults:

    def test_empty_returns_no_documents_message(self):
        result = _format_results([], [])
        assert result == "No relevant documents found."

    def test_single_result_contains_source(self):
        result = _format_results(["Some content."], [{"source": "sales.csv"}])
        assert "Source: sales.csv" in result
        assert "Some content." in result

    def test_numbered_from_one(self):
        docs = ["chunk a", "chunk b"]
        metas = [{"source": "a.txt"}, {"source": "b.txt"}]
        result = _format_results(docs, metas)
        assert "[1]" in result
        assert "[2]" in result

    def test_multiple_results_separated_by_divider(self):
        docs = ["chunk a", "chunk b"]
        metas = [{"source": "a.txt"}, {"source": "b.txt"}]
        result = _format_results(docs, metas)
        assert "---" in result

    def test_missing_source_falls_back_to_unknown(self):
        result = _format_results(["text"], [{}])
        assert "unknown source" in result

    def test_content_is_stripped(self):
        result = _format_results(["  padded content  "], [{"source": "f.txt"}])
        assert "padded content" in result
        assert "  padded content  " not in result


# ===========================================================================
# _rerank()
# ===========================================================================

class TestRerank:

    def test_returns_top_k_results(self, mock_reranker):
        docs = [f"doc {i}" for i in range(10)]
        metas = [{"source": f"f{i}.txt"} for i in range(10)]
        result_docs, result_metas = _rerank("query", docs, metas, top_k=3)
        assert len(result_docs) == 3
        assert len(result_metas) == 3

    def test_fewer_candidates_than_top_k_returns_all(self, mock_reranker):
        docs = ["doc a", "doc b"]
        metas = [{"source": "a.txt"}, {"source": "b.txt"}]
        result_docs, result_metas = _rerank("query", docs, metas, top_k=5)
        assert len(result_docs) == 2

    def test_returns_tuple_of_two_lists(self, mock_reranker):
        docs = ["d1", "d2", "d3"]
        metas = [{"source": f"f{i}.txt"} for i in range(3)]
        result = _rerank("query", docs, metas, top_k=2)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    def test_docs_and_metas_stay_aligned(self, mock_reranker):
        """After reranking, each doc must still match its metadata."""
        # mock_reranker reverses order, so we verify the reversal is consistent
        docs = ["doc_0", "doc_1", "doc_2"]
        metas = [{"source": f"file_{i}.txt"} for i in range(3)]
        result_docs, result_metas = _rerank("query", docs, metas, top_k=3)
        # reversed: doc_2 → file_2, doc_1 → file_1, doc_0 → file_0
        for doc, meta in zip(result_docs, result_metas):
            idx = doc.split("_")[1]
            assert meta["source"] == f"file_{idx}.txt"


# ===========================================================================
# build_rag_tool()
# ===========================================================================

class TestBuildRagTool:

    def test_returns_a_tool(self, mock_chroma):
        from langchain_core.tools import BaseTool
        tool = build_rag_tool("cafe")
        assert isinstance(tool, BaseTool)

    def test_tool_name_is_search_documents(self, mock_chroma):
        tool = build_rag_tool("cafe")
        assert tool.name == "search_documents"

    def test_unknown_key_raises_at_build_time(self, mock_chroma):
        with pytest.raises(KeyError):
            build_rag_tool("unknown_biz")

    def test_all_three_business_keys_build_without_error(self, mock_chroma):
        for key in ("cafe", "hotel", "gems"):
            tool = build_rag_tool(key)
            assert tool is not None


# ===========================================================================
# search_documents() — the tool in action
# ===========================================================================

class TestSearchDocuments:

    def test_collection_not_found_returns_helpful_message(
        self, mock_chroma, mock_embedder
    ):
        # Collection exists in config but hasn't been created in ChromaDB yet
        rag_tool = build_rag_tool("cafe")
        result = rag_tool.invoke({"query": "What is the revenue?"})
        assert "No documents have been indexed" in result

    def test_happy_path_returns_formatted_context(
        self, mock_chroma, mock_embedder, mock_reranker
    ):
        seed_collection(mock_chroma, "cafe_restaurant", n=3)
        rag_tool = build_rag_tool("cafe")
        result = rag_tool.invoke({"query": "business content"})
        assert "[1]" in result
        assert "Source:" in result

    def test_result_contains_seeded_content(
        self, mock_chroma, mock_embedder, mock_reranker
    ):
        seed_collection(mock_chroma, "airport_hotel", n=5)
        rag_tool = build_rag_tool("hotel")
        result = rag_tool.invoke({"query": "hotel topic"})
        assert "business content" in result

    def test_reranker_called_when_candidates_exceed_top_k(
        self, mock_chroma, mock_embedder, mock_reranker
    ):
        # With n > top_k (5), RERANK_FETCH_MULTIPLIER kicks in and reranker runs
        seed_collection(mock_chroma, "gem_business", n=20)
        rag_tool = build_rag_tool("gems")
        rag_tool.invoke({"query": "gem quality"})
        assert mock_reranker.rerank.called

    def test_reranker_skipped_when_candidates_lte_top_k(
        self, mock_chroma, mock_embedder, mock_reranker
    ):
        # With only 2 docs (< top_k=5), reranker should NOT be called
        seed_collection(mock_chroma, "cafe_restaurant", n=2)
        rag_tool = build_rag_tool("cafe")
        rag_tool.invoke({"query": "revenue"})
        assert not mock_reranker.rerank.called

    def test_embed_query_called_with_user_query(
        self, mock_chroma, mock_embedder, mock_reranker
    ):
        seed_collection(mock_chroma, "cafe_restaurant", n=3)
        rag_tool = build_rag_tool("cafe")
        rag_tool.invoke({"query": "daily sales"})
        mock_embedder.embed_query.assert_called_once_with("daily sales")
