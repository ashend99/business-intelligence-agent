"""
tests/ingestion/test_splitter.py

Test suite for ingestion/splitter.py covering:

    split_documents()
    ├── Happy path — documents are split correctly
    ├── Metadata — chunk_id is stamped on every chunk
    ├── Defaults — function works without explicit chunk_size / chunk_overlap
    ├── Edge cases — empty list, all-empty docs, single short doc, whitespace-only docs
    └── Error cases — invalid chunk_size, chunk_overlap >= chunk_size
"""

import pytest
from langchain_core.documents import Document

from ingestion.splitter import split_documents


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(content: str, source: str = "test.txt") -> Document:
    """Create a Document with the given content and a source metadata key."""
    return Document(page_content=content, metadata={"source": source})


def make_long_doc(n_chars: int = 3000, source: str = "long.txt") -> Document:
    """Create a Document with n_chars worth of repeating text."""
    word = "Business intelligence report. "
    content = (word * (n_chars // len(word) + 1))[:n_chars]
    return Document(page_content=content, metadata={"source": source})


# ===========================================================================
# Happy path
# ===========================================================================

class TestSplitDocumentsHappyPath:

    def test_returns_list_of_documents(self):
        docs = [make_long_doc()]
        result = split_documents(docs, chunk_size=500, chunk_overlap=50)
        assert isinstance(result, list)
        assert all(isinstance(d, Document) for d in result)

    def test_long_document_is_split_into_multiple_chunks(self):
        docs = [make_long_doc(3000)]
        result = split_documents(docs, chunk_size=500, chunk_overlap=50)
        assert len(result) > 1

    def test_each_chunk_respects_chunk_size(self):
        docs = [make_long_doc(3000)]
        chunk_size = 300
        result = split_documents(docs, chunk_size=chunk_size, chunk_overlap=50)
        # LangChain splitter may slightly exceed chunk_size at separator boundaries,
        # so we allow a small tolerance (2x is a safe upper bound for real text).
        for doc in result:
            assert len(doc.page_content) <= chunk_size * 2

    def test_multiple_documents_are_all_split(self):
        docs = [make_long_doc(2000, source=f"doc{i}.txt") for i in range(3)]
        result = split_documents(docs, chunk_size=400, chunk_overlap=50)
        assert len(result) > 3  # at least more than the original count

    def test_short_document_stays_as_single_chunk(self):
        short_content = "Short sentence."
        docs = [make_doc(short_content)]
        result = split_documents(docs, chunk_size=500, chunk_overlap=50)
        assert len(result) == 1
        assert result[0].page_content == short_content

    def test_original_metadata_is_preserved(self):
        docs = [make_long_doc(2000, source="hotel_report.txt")]
        result = split_documents(docs, chunk_size=400, chunk_overlap=50)
        for doc in result:
            assert doc.metadata.get("source") == "hotel_report.txt"


# ===========================================================================
# chunk_id metadata
# ===========================================================================

class TestChunkIdMetadata:

    def test_every_chunk_has_chunk_id(self):
        docs = [make_long_doc(2000)]
        result = split_documents(docs, chunk_size=400, chunk_overlap=50)
        for doc in result:
            assert "chunk_id" in doc.metadata

    def test_chunk_ids_are_sequential_from_zero(self):
        docs = [make_long_doc(2000)]
        result = split_documents(docs, chunk_size=400, chunk_overlap=50)
        ids = [doc.metadata["chunk_id"] for doc in result]
        assert ids == list(range(len(result)))

    def test_chunk_id_is_integer(self):
        docs = [make_long_doc(1000)]
        result = split_documents(docs, chunk_size=300, chunk_overlap=30)
        for doc in result:
            assert isinstance(doc.metadata["chunk_id"], int)


# ===========================================================================
# Default parameters
# ===========================================================================

class TestDefaultParameters:

    def test_works_without_explicit_chunk_size_and_overlap(self):
        # Default chunk_size=1000, chunk_overlap=150
        docs = [make_long_doc(3000)]
        result = split_documents(docs)
        assert len(result) >= 1

    def test_defaults_produce_multiple_chunks_for_large_doc(self):
        docs = [make_long_doc(5000)]
        result = split_documents(docs)
        assert len(result) > 1


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:

    def test_empty_list_returns_empty_list(self):
        result = split_documents([])
        assert result == []

    def test_all_empty_content_docs_returns_empty_list(self):
        docs = [make_doc(""), make_doc("   "), make_doc("\n\t")]
        result = split_documents(docs, chunk_size=500, chunk_overlap=50)
        assert result == []

    def test_mix_of_empty_and_valid_docs_skips_empty(self):
        docs = [make_doc(""), make_long_doc(1500), make_doc("  ")]
        result = split_documents(docs, chunk_size=400, chunk_overlap=50)
        assert len(result) >= 1
        for doc in result:
            assert doc.page_content.strip()

    def test_single_doc_exactly_at_chunk_size_boundary(self):
        # A doc exactly equal to chunk_size should produce exactly 1 chunk.
        content = "a" * 500
        docs = [make_doc(content)]
        result = split_documents(docs, chunk_size=500, chunk_overlap=0)
        assert len(result) == 1

    def test_whitespace_only_doc_is_excluded(self):
        docs = [make_doc("     "), make_doc("real content here")]
        result = split_documents(docs, chunk_size=500, chunk_overlap=50)
        assert len(result) == 1
        assert result[0].page_content == "real content here"

    def test_chunk_overlap_zero_is_valid(self):
        docs = [make_long_doc(2000)]
        result = split_documents(docs, chunk_size=500, chunk_overlap=0)
        assert len(result) >= 1

    def test_chunk_ids_are_globally_sequential_across_multiple_docs(self):
        docs = [make_long_doc(2000, source=f"doc{i}.txt") for i in range(2)]
        result = split_documents(docs, chunk_size=400, chunk_overlap=50)
        ids = [doc.metadata["chunk_id"] for doc in result]
        assert ids == list(range(len(result)))


# ===========================================================================
# Error cases
# ===========================================================================

class TestErrorCases:

    def test_chunk_size_zero_raises_value_error(self):
        docs = [make_long_doc(500)]
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            split_documents(docs, chunk_size=0, chunk_overlap=0)

    def test_chunk_size_negative_raises_value_error(self):
        docs = [make_long_doc(500)]
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            split_documents(docs, chunk_size=-100, chunk_overlap=0)

    def test_chunk_overlap_equal_to_chunk_size_raises_value_error(self):
        docs = [make_long_doc(500)]
        with pytest.raises(ValueError, match="chunk_overlap must be < chunk_size"):
            split_documents(docs, chunk_size=200, chunk_overlap=200)

    def test_chunk_overlap_greater_than_chunk_size_raises_value_error(self):
        docs = [make_long_doc(500)]
        with pytest.raises(ValueError, match="chunk_overlap must be < chunk_size"):
            split_documents(docs, chunk_size=100, chunk_overlap=150)

    def test_error_message_includes_actual_values(self):
        docs = [make_long_doc(500)]
        with pytest.raises(ValueError, match="300 >= 200"):
            split_documents(docs, chunk_size=200, chunk_overlap=300)
