"""
tests/ingestion/test_loader.py

Test suite for ingestion/loader.py covering:

    load_document()
    ├── Happy path — each supported file type loads correctly
    ├── Metadata — source key is always present
    ├── Edge cases — empty file, file with special characters
    └── Error cases — missing file, unsupported extension

    load_directory()
    ├── Happy path — loads all supported files recursively
    ├── Extension filter — only requested types are loaded
    ├── Unsupported files — silently skipped
    ├── Empty directory — returns empty list
    └── Error case — directory does not exist
"""

from pathlib import Path

import pytest
from langchain_core.documents import Document

from ingestion.loader import load_directory, load_document


# ===========================================================================
# load_document() — happy path
# ===========================================================================

class TestLoadDocumentHappyPath:

    def test_txt_returns_documents(self, txt_file: Path):
        docs = load_document(txt_file)
        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)

    def test_txt_content_is_not_empty(self, txt_file: Path):
        docs = load_document(txt_file)
        assert any(d.page_content.strip() for d in docs)

    def test_txt_contains_expected_text(self, txt_file: Path):
        docs = load_document(txt_file)
        combined = " ".join(d.page_content for d in docs)
        assert "Café" in combined or "Revenue" in combined

    def test_csv_returns_documents(self, csv_file: Path):
        docs = load_document(csv_file)
        assert len(docs) >= 1

    def test_csv_each_row_is_a_document(self, csv_file: Path):
        # CSVLoader creates one Document per data row (excluding header)
        docs = load_document(csv_file)
        assert len(docs) == 3  # 3 data rows in the fixture

    def test_csv_content_contains_field_values(self, csv_file: Path):
        docs = load_document(csv_file)
        combined = " ".join(d.page_content for d in docs)
        assert "Espresso" in combined

    def test_docx_returns_documents(self, docx_file: Path):
        docs = load_document(docx_file)
        assert len(docs) >= 1

    def test_docx_content_contains_text(self, docx_file: Path):
        docs = load_document(docx_file)
        combined = " ".join(d.page_content for d in docs)
        assert "gem" in combined.lower() or "brand" in combined.lower()

    def test_xlsx_returns_documents(self, xlsx_file: Path):
        docs = load_document(xlsx_file)
        assert len(docs) >= 1

    def test_xlsx_content_is_not_empty(self, xlsx_file: Path):
        docs = load_document(xlsx_file)
        assert any(d.page_content.strip() for d in docs)


# ===========================================================================
# load_document() — metadata
# ===========================================================================

class TestLoadDocumentMetadata:

    def test_txt_metadata_has_source(self, txt_file: Path):
        docs = load_document(txt_file)
        for doc in docs:
            assert "source" in doc.metadata

    def test_csv_metadata_has_source(self, csv_file: Path):
        docs = load_document(csv_file)
        for doc in docs:
            assert "source" in doc.metadata

    def test_docx_metadata_has_source(self, docx_file: Path):
        docs = load_document(docx_file)
        for doc in docs:
            assert "source" in doc.metadata

    def test_xlsx_metadata_has_source(self, xlsx_file: Path):
        docs = load_document(xlsx_file)
        for doc in docs:
            assert "source" in doc.metadata

    def test_source_points_to_correct_file(self, txt_file: Path):
        docs = load_document(txt_file)
        for doc in docs:
            assert str(txt_file) in doc.metadata["source"]


# ===========================================================================
# load_document() — edge cases
# ===========================================================================

class TestLoadDocumentEdgeCases:

    def test_empty_txt_file_does_not_raise(self, empty_txt_file: Path):
        # An empty file should return an empty list or a single empty Document
        # but must not raise an exception
        docs = load_document(empty_txt_file)
        assert isinstance(docs, list)

    def test_txt_with_special_characters(self, txt_file_utf8_special: Path):
        docs = load_document(txt_file_utf8_special)
        combined = " ".join(d.page_content for d in docs)
        assert "Café" in combined or "résumé" in combined

    def test_accepts_string_path(self, txt_file: Path):
        # load_document should accept str in addition to Path
        docs = load_document(str(txt_file))
        assert len(docs) >= 1

    def test_accepts_relative_path(self, txt_file: Path, monkeypatch: pytest.MonkeyPatch):
        # Change cwd to the file's parent so a relative path resolves correctly
        monkeypatch.chdir(txt_file.parent)
        docs = load_document(Path(txt_file.name))
        assert len(docs) >= 1


# ===========================================================================
# load_document() — error cases
# ===========================================================================

class TestLoadDocumentErrors:

    def test_raises_file_not_found(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist.txt"
        with pytest.raises(FileNotFoundError, match="File not found"):
            load_document(missing)

    def test_raises_value_error_for_unsupported_extension(self, unsupported_file: Path):
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_document(unsupported_file)

    def test_error_message_lists_supported_types(self, unsupported_file: Path):
        with pytest.raises(ValueError) as exc_info:
            load_document(unsupported_file)
        assert ".pdf" in str(exc_info.value)

    def test_raises_for_directory_instead_of_file(self, tmp_path: Path):
        # Passing a directory path should raise FileNotFoundError or ValueError
        with pytest.raises((FileNotFoundError, ValueError, IsADirectoryError)):
            load_document(tmp_path)


# ===========================================================================
# load_directory() — happy path
# ===========================================================================

class TestLoadDirectoryHappyPath:

    def test_returns_documents_from_all_supported_files(self, docs_directory: Path):
        docs = load_directory(docs_directory)
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

    def test_loads_files_from_all_subdirectories(self, docs_directory: Path):
        docs = load_directory(docs_directory)
        sources = {d.metadata.get("source", "") for d in docs}
        # At least files from two different sub-directories must appear
        subdirs_found = {
            subdir
            for subdir in ["cafe", "hotel", "gems"]
            if any(subdir in s for s in sources)
        }
        assert len(subdirs_found) >= 2

    def test_all_documents_have_source_metadata(self, docs_directory: Path):
        docs = load_directory(docs_directory)
        for doc in docs:
            assert "source" in doc.metadata

    def test_unsupported_files_are_skipped(self, docs_directory: Path):
        docs = load_directory(docs_directory)
        sources = [d.metadata.get("source", "") for d in docs]
        assert not any(".png" in s for s in sources)


# ===========================================================================
# load_directory() — extension filter
# ===========================================================================

class TestLoadDirectoryExtensionFilter:

    def test_filter_to_txt_only(self, docs_directory: Path):
        docs = load_directory(docs_directory, extensions=[".txt"])
        sources = [d.metadata.get("source", "") for d in docs]
        assert all(s.endswith(".txt") for s in sources)

    def test_filter_to_csv_only(self, docs_directory: Path):
        docs = load_directory(docs_directory, extensions=[".csv"])
        sources = [d.metadata.get("source", "") for d in docs]
        assert all(s.endswith(".csv") for s in sources)

    def test_filter_to_multiple_types(self, docs_directory: Path):
        docs = load_directory(docs_directory, extensions=[".txt", ".csv"])
        sources = [d.metadata.get("source", "") for d in docs]
        for s in sources:
            assert s.endswith(".txt") or s.endswith(".csv")

    def test_filter_returns_empty_when_no_match(self, docs_directory: Path):
        # No .py files exist in the fixture directory
        docs = load_directory(docs_directory, extensions=[".py"])
        assert docs == []


# ===========================================================================
# load_directory() — edge and error cases
# ===========================================================================

class TestLoadDirectoryEdgeCases:

    def test_empty_directory_returns_empty_list(self, tmp_path: Path):
        docs = load_directory(tmp_path)
        assert docs == []

    def test_raises_for_missing_directory(self, tmp_path: Path):
        missing = tmp_path / "no_such_folder"
        with pytest.raises(FileNotFoundError, match="Directory not found"):
            load_directory(missing)

    def test_corrupt_file_does_not_crash_directory_load(self, tmp_path: Path):
        # Write a .pdf file with invalid content — loader should fail gracefully
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_bytes(b"this is not a real pdf")
        # Should not raise — bad files are caught internally and skipped
        docs = load_directory(tmp_path)
        assert isinstance(docs, list)
