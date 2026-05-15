"""
Module: ingestion/upload_docs.py

DocumentUploadPipeline — orchestrates the full ingestion flow for a single
business collection: load → split → index.

Usage:
    from pathlib import Path
    from ingestion.upload_docs import DocumentUploadPipeline

    pipeline = DocumentUploadPipeline(business_key="cafe")
    result = pipeline.run([Path("docs/menu.pdf"), Path("docs/prices.xlsx")])
    print(result)
    # {'files_processed': 2, 'chunks_indexed': 47, 'errors': []}
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document

from config.settings import settings
from ingestion.indexer import index_documents, _resolve_collection_name
from ingestion.loader import load_document
from ingestion.splitter import split_documents

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Summary returned by DocumentUploadPipeline.run()."""
    files_processed: int = 0
    chunks_indexed: int = 0
    errors: list[dict] = field(default_factory=list)

    def __str__(self) -> str:
        status = "OK" if not self.errors else f"{len(self.errors)} error(s)"
        return (
            f"UploadResult(files={self.files_processed}, "
            f"chunks={self.chunks_indexed}, status={status})"
        )


class DocumentUploadPipeline:
    """Ingestion pipeline: load → split → index for a given business.

    Each call to ``run()`` accepts a list of file paths, processes them
    through the three ingestion stages, and returns an ``UploadResult``
    summary. Files that fail at any stage are recorded in
    ``result.errors`` and processing continues for the remaining files.

    Args:
        business_key: Short key identifying the target collection
                      (e.g. 'cafe', 'hotel', 'gems'). Must exist in
                      config.yaml under vectorstore.collections.
        chunk_size:   Character limit per chunk (default from settings).
        chunk_overlap: Overlap between consecutive chunks (default from settings).

    Raises:
        KeyError: On construction if business_key is not configured.
    """

    def __init__(
        self,
        business_key: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        # Validate the key up-front so the caller gets an immediate error
        _resolve_collection_name(business_key)

        self.business_key = business_key
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        logger.debug(
            "DocumentUploadPipeline initialised for '%s' "
            "(chunk_size=%d, chunk_overlap=%d)",
            business_key, self.chunk_size, self.chunk_overlap,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, file_paths: list[Path]) -> UploadResult:
        """Run the full load → split → index pipeline on a list of files.

        Args:
            file_paths: List of Path objects pointing to the documents to
                        ingest. Supported formats are determined by
                        ingestion/loader.py.

        Returns:
            UploadResult with counts and any per-file errors.
        """
        result = UploadResult()

        for path in file_paths:
            try:
                chunks = self._process_file(path)
                if not chunks:
                    logger.warning("No chunks produced from '%s' — skipping.", path)
                    continue

                indexed = index_documents(chunks, self.business_key)
                result.files_processed += 1
                result.chunks_indexed += indexed
                logger.info(
                    "[%s] '%s' → %d chunk(s) indexed.",
                    self.business_key, path.name, indexed,
                )

            except Exception as exc:  # noqa: BLE001
                error = {"file": str(path), "error": str(exc)}
                result.errors.append(error)
                logger.error("Failed to process '%s': %s", path, exc)

        return result

    def run_one(self, file_path: Path) -> UploadResult:
        """Convenience wrapper to run the pipeline for a single file.

        Args:
            file_path: Path to the document to ingest.

        Returns:
            UploadResult for that single file.
        """
        return self.run([file_path])

    # ------------------------------------------------------------------
    # Internal stages
    # ------------------------------------------------------------------

    def _process_file(self, path: Path) -> list[Document]:
        """Load and split a single file into indexable chunks."""
        logger.debug("Loading '%s'...", path)
        docs = load_document(path)

        logger.debug("Splitting %d page(s) from '%s'...", len(docs), path)
        chunks = split_documents(
            docs,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return chunks
