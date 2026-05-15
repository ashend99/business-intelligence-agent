"""
tests/ingestion/test_upload_docs.py

Test suite for ingestion/upload_docs.py covering:

    DocumentUploadPipeline.__init__()
    ├── Valid business_key — constructs without error
    ├── Unknown business_key — raises KeyError immediately
    └── Custom chunk parameters — stored on the instance

    DocumentUploadPipeline.run()
    ├── Happy path — correct files_processed and chunks_indexed
    ├── Multiple files — counts accumulate across files
    ├── File that fails to load — recorded in errors, others continue
    ├── File producing no chunks — skipped, files_processed unchanged
    └── Empty file list — returns zero counts, no errors

    DocumentUploadPipeline.run_one()
    └── Delegates to run() with a single-element list

All file I/O and OpenAI calls are mocked. ChromaDB is replaced with an
isolated in-memory manager via the get_vector_db() patch used by indexer.py.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from langchain_core.documents import Document

from ingestion.upload_docs import DocumentUploadPipeline, UploadResult
from ingestion.vectordb import ChromaDBManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def chroma_manager(monkeypatch, tmp_path):
    """Isolated ChromaDBManager; patch both indexer and vectordb factory."""
    manager = ChromaDBManager.__new__(ChromaDBManager)
    manager._client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))

    monkeypatch.setattr("ingestion.indexer.get_vector_db", lambda: manager)
    return manager


@pytest.fixture()
def mock_embedder(monkeypatch):
    """Replace OpenAI embedder with a mock that returns fake vectors."""
    embedder = MagicMock()
    embedder.embed_documents.side_effect = lambda texts: [[0.1, 0.2, 0.3]] * len(texts)
    monkeypatch.setattr("ingestion.indexer._get_embedder", lambda: embedder)
    return embedder


def _make_docs(n: int, source: str = "test.txt") -> list[Document]:
    return [Document(page_content=f"content {i}", metadata={"source": source}) for i in range(n)]


# ---------------------------------------------------------------------------
# Helpers to mock load_document and split_documents
# ---------------------------------------------------------------------------

def patch_load(docs: list[Document]):
    return patch("ingestion.upload_docs.load_document", return_value=docs)


def patch_split(chunks: list[Document]):
    return patch("ingestion.upload_docs.split_documents", return_value=chunks)


# ===========================================================================
# __init__()
# ===========================================================================

class TestInit:

    def test_valid_business_key_constructs(self):
        pipeline = DocumentUploadPipeline("cafe")
        assert pipeline.business_key == "cafe"

    def test_unknown_key_raises_key_error(self):
        with pytest.raises(KeyError):
            DocumentUploadPipeline("unknown_biz")

    def test_default_chunk_params_come_from_settings(self, monkeypatch):
        monkeypatch.setattr("ingestion.upload_docs.settings.chunk_size", 500)
        monkeypatch.setattr("ingestion.upload_docs.settings.chunk_overlap", 50)
        pipeline = DocumentUploadPipeline("cafe")
        assert pipeline.chunk_size == 500
        assert pipeline.chunk_overlap == 50

    def test_custom_chunk_params_are_stored(self):
        pipeline = DocumentUploadPipeline("hotel", chunk_size=800, chunk_overlap=80)
        assert pipeline.chunk_size == 800
        assert pipeline.chunk_overlap == 80

    def test_all_three_business_keys_are_valid(self):
        for key in ("cafe", "hotel", "gems"):
            DocumentUploadPipeline(key)


# ===========================================================================
# run() — happy path
# ===========================================================================

class TestRunHappyPath:

    def test_single_file_files_processed_is_one(self, chroma_manager, mock_embedder):
        chunks = _make_docs(3, source="menu.pdf")
        with patch_load(_make_docs(1)), patch_split(chunks):
            pipeline = DocumentUploadPipeline("cafe")
            result = pipeline.run([Path("menu.pdf")])

        assert result.files_processed == 1

    def test_single_file_chunks_indexed(self, chroma_manager, mock_embedder):
        chunks = _make_docs(5, source="menu.pdf")
        with patch_load(_make_docs(1)), patch_split(chunks):
            pipeline = DocumentUploadPipeline("cafe")
            result = pipeline.run([Path("menu.pdf")])

        assert result.chunks_indexed == 5

    def test_no_errors_on_success(self, chroma_manager, mock_embedder):
        with patch_load(_make_docs(2)), patch_split(_make_docs(4)):
            result = DocumentUploadPipeline("hotel").run([Path("rates.pdf")])

        assert result.errors == []

    def test_result_is_upload_result_instance(self, chroma_manager, mock_embedder):
        with patch_load(_make_docs(1)), patch_split(_make_docs(2)):
            result = DocumentUploadPipeline("gems").run([Path("catalogue.pdf")])

        assert isinstance(result, UploadResult)


# ===========================================================================
# run() — multiple files
# ===========================================================================

class TestRunMultipleFiles:

    def test_counts_accumulate_across_files(self, chroma_manager, mock_embedder):
        # file_a → 3 chunks, file_b → 4 chunks
        call_count = {"n": 0}
        chunk_counts = [3, 4]

        def fake_split(docs, **kwargs):
            n = chunk_counts[call_count["n"]]
            call_count["n"] += 1
            return _make_docs(n)

        with patch_load(_make_docs(1)), \
             patch("ingestion.upload_docs.split_documents", side_effect=fake_split):
            result = DocumentUploadPipeline("cafe").run(
                [Path("file_a.pdf"), Path("file_b.pdf")]
            )

        assert result.files_processed == 2
        assert result.chunks_indexed == 7

    def test_empty_file_list_returns_zero_counts(self, chroma_manager, mock_embedder):
        result = DocumentUploadPipeline("cafe").run([])
        assert result.files_processed == 0
        assert result.chunks_indexed == 0
        assert result.errors == []


# ===========================================================================
# run() — error handling
# ===========================================================================

class TestRunErrors:

    def test_load_failure_recorded_in_errors(self, chroma_manager, mock_embedder):
        with patch("ingestion.upload_docs.load_document", side_effect=ValueError("bad file")):
            result = DocumentUploadPipeline("cafe").run([Path("bad.pdf")])

        assert result.files_processed == 0
        assert len(result.errors) == 1
        assert "bad.pdf" in result.errors[0]["file"]
        assert "bad file" in result.errors[0]["error"]

    def test_processing_continues_after_one_failure(self, chroma_manager, mock_embedder):
        good_chunks = _make_docs(3, source="good.pdf")
        call_count = {"n": 0}

        def selective_load(path):
            call_count["n"] += 1
            if "bad" in str(path):
                raise OSError("cannot read")
            return _make_docs(1, source=str(path))

        with patch("ingestion.upload_docs.load_document", side_effect=selective_load), \
             patch_split(good_chunks):
            result = DocumentUploadPipeline("cafe").run(
                [Path("bad.pdf"), Path("good.pdf")]
            )

        assert result.files_processed == 1
        assert result.chunks_indexed == 3
        assert len(result.errors) == 1

    def test_no_chunks_skips_file_without_error(self, chroma_manager, mock_embedder):
        with patch_load(_make_docs(1)), patch_split([]):
            result = DocumentUploadPipeline("hotel").run([Path("empty.pdf")])

        assert result.files_processed == 0
        assert result.chunks_indexed == 0
        assert result.errors == []


# ===========================================================================
# run_one()
# ===========================================================================

class TestRunOne:

    def test_run_one_delegates_to_run(self, chroma_manager, mock_embedder):
        chunks = _make_docs(2, source="single.pdf")
        with patch_load(_make_docs(1)), patch_split(chunks):
            result = DocumentUploadPipeline("cafe").run_one(Path("single.pdf"))

        assert result.files_processed == 1
        assert result.chunks_indexed == 2

    def test_run_one_returns_upload_result(self, chroma_manager, mock_embedder):
        with patch_load(_make_docs(1)), patch_split(_make_docs(1)):
            result = DocumentUploadPipeline("gems").run_one(Path("gem_data.csv"))

        assert isinstance(result, UploadResult)


# ===========================================================================
# UploadResult
# ===========================================================================

class TestUploadResult:

    def test_str_shows_ok_when_no_errors(self):
        r = UploadResult(files_processed=3, chunks_indexed=42)
        assert "OK" in str(r)
        assert "3" in str(r)
        assert "42" in str(r)

    def test_str_shows_error_count_when_errors_present(self):
        r = UploadResult(errors=[{"file": "x", "error": "bad"}])
        assert "1 error" in str(r)

    def test_default_values_are_zero(self):
        r = UploadResult()
        assert r.files_processed == 0
        assert r.chunks_indexed == 0
        assert r.errors == []
