"""
Module: ingestion/loader.py
Date: 2026-05-08

Loads documents from the filesystem into LangChain Document objects.

Supported formats:
    .pdf    — PDF files (text-based)
    .docx   — Microsoft Word documents
    .xlsx   — Microsoft Excel spreadsheets
    .csv    — Comma-separated values
    .txt    — Plain text files

Each loader returns a list of Document objects. A Document has two fields:
    - page_content : str   — the raw text extracted from the file
    - metadata     : dict  — source file path, page number, sheet name, etc.

Usage:
    from ingestion.loader import load_document

    docs = load_document(Path("docs/cafe/menu.pdf"))
"""

from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredExcelLoader,
)
from langchain_core.documents import Document


# Map file extensions to their loader classes
_LOADER_MAP = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".csv":  CSVLoader,
    ".txt":  TextLoader,
}


def load_document(file_path: Path) -> list[Document]:
    """
    Load a single file and return its contents as a list of Documents.

    Each page / row / sheet may become a separate Document depending on
    the loader used. All Documents carry a 'source' key in their metadata
    pointing back to the original file path.

    Args:
        file_path: Absolute or relative path to the document.

    Returns:
        List of LangChain Document objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is not supported.
    """
    # Get file path as absolute Path object for consistent handling
    file_path = Path(file_path).resolve()

    # Check file existence
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check file extension and get corresponding loader
    suffix = file_path.suffix.lower()
    if suffix not in _LOADER_MAP:
        raise ValueError(
            f"Unsupported file type: '{suffix}'\n"
            f"Supported types: {list(_LOADER_MAP.keys())}"
        )
    loader_cls = _LOADER_MAP[suffix]

    # TextLoader needs explicit encoding to handle non-ASCII characters safely
    if suffix == ".txt":
        loader = loader_cls(str(file_path), encoding="utf-8")
    else:
        loader = loader_cls(str(file_path))

    docs = loader.load()

    # Ensure every document carries the source path in metadata
    for doc in docs:
        doc.metadata.setdefault("source", str(file_path))

    return docs


def load_directory(directory: Path, extensions: list[str] | None = None) -> list[Document]:
    """
    Recursively load all supported documents from a directory.

    Args:
        directory:  Path to the folder to scan.
        extensions: Optional list of extensions to filter (e.g. ['.pdf', '.csv']).
                    Defaults to all supported types.

    Returns:
        Combined list of Documents from all files found.
    """
    # Get absolute path of the directory for consistent handling
    directory = Path(directory).resolve()

    # Check directory existence
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    # Determine which file extensions to allow based on input or default to all
    allowed = set(extensions) if extensions else set(_LOADER_MAP.keys())
    all_docs: list[Document] = []
    failed: list[str] = []

    # Recursively scan the directory for files with allowed extensions and 
    # attempt to load them into Documents
    for file_path in sorted(directory.rglob("*")):
        if file_path.suffix.lower() not in allowed:
            continue

        try:
            docs = load_document(file_path)
            all_docs.extend(docs)
            print(f"  ✅  Loaded {len(docs):>3} chunk(s)  ←  {file_path.name}")
        except Exception as e:
            failed.append(str(file_path))
            print(f"  ❌  Failed to load {file_path.name}: {e}")

    if failed:
        print(f"\n⚠️  {len(failed)} file(s) could not be loaded.")

    return all_docs
