"""
tests/api/conftest.py

Shared fixtures for API tests.

Strategy:
  - Use FastAPI's TestClient (synchronous httpx wrapper) — no real server needed.
  - Patch DocumentUploadPipeline.run so no embeddings / ChromaDB calls are made.
  - Patch list_documents / get_collection_count for read endpoints.
"""

import csv
import textwrap
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from ingestion.upload_docs import UploadResult


# ---------------------------------------------------------------------------
# App client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a TestClient that exercises the FastAPI app in-process."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Dummy pipeline result
# ---------------------------------------------------------------------------

@pytest.fixture()
def ok_pipeline_result() -> UploadResult:
    return UploadResult(files_processed=1, chunks_indexed=12, errors=[])


@pytest.fixture()
def error_pipeline_result() -> UploadResult:
    return UploadResult(
        files_processed=0,
        chunks_indexed=0,
        errors=[{"file": "bad.txt", "error": "Unsupported format"}],
    )


# ---------------------------------------------------------------------------
# Sample in-memory files
# ---------------------------------------------------------------------------

@pytest.fixture()
def txt_bytes() -> bytes:
    return textwrap.dedent("""\
        LUSTER Cafe — Daily Summary
        Date: 2026-05-15
        Revenue: $5,200.00
    """).encode()


@pytest.fixture()
def csv_bytes() -> bytes:
    buf = BytesIO()
    import io, csv as _csv
    s = io.StringIO()
    w = _csv.writer(s)
    w.writerow(["date", "item", "qty"])
    w.writerow(["2026-05-15", "Latte", "40"])
    return s.getvalue().encode()
