"""
tests/api/test_upload.py

Unit tests for POST /api/documents/upload/{business_key}

All external I/O (pipeline run, embeddings, ChromaDB) is mocked so tests
are fast and require no network or disk state.
"""

from unittest.mock import MagicMock, patch

import pytest
from ingestion.upload_docs import UploadResult


UPLOAD_URL = "/api/documents/upload/{key}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload(client, key: str, files: list[tuple], **kwargs):
    """POST multipart files to the upload endpoint."""
    return client.post(
        UPLOAD_URL.format(key=key),
        files=files,
        **kwargs,
    )


def _txt_file(name: str = "report.txt", content: bytes = b"hello world") -> tuple:
    return ("files", (name, content, "text/plain"))


def _csv_file(name: str = "sales.csv", content: bytes = b"date,item\n2026-05-15,Latte") -> tuple:
    return ("files", (name, content, "text/csv"))


# ---------------------------------------------------------------------------
# Valid key — happy paths
# ---------------------------------------------------------------------------

class TestUploadHappyPath:

    def test_single_txt_file_returns_200(self, client, ok_pipeline_result):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = ok_pipeline_result
            resp = _upload(client, "luster", [_txt_file()])

        assert resp.status_code == 200

    def test_response_contains_expected_keys(self, client, ok_pipeline_result):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = ok_pipeline_result
            resp = _upload(client, "luster", [_txt_file()])

        body = resp.json()
        assert "files_processed" in body
        assert "chunks_indexed" in body
        assert "errors" in body

    def test_single_file_counts(self, client, ok_pipeline_result):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = ok_pipeline_result
            resp = _upload(client, "luster", [_txt_file()])

        body = resp.json()
        assert body["files_processed"] == 1
        assert body["chunks_indexed"] == 12
        assert body["errors"] == []

    def test_multiple_files_accepted(self, client):
        result = UploadResult(files_processed=2, chunks_indexed=25, errors=[])
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = result
            resp = _upload(client, "luster", [_txt_file("a.txt"), _csv_file("b.csv")])

        assert resp.status_code == 200
        assert resp.json()["files_processed"] == 2

    def test_pipeline_receives_original_filename(self, client, ok_pipeline_result):
        """The pipeline should be called with a path whose name matches the upload."""
        captured = {}

        def fake_run(paths):
            captured["names"] = [p.name for p in paths]
            return ok_pipeline_result

        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = fake_run
            _upload(client, "luster", [_txt_file("my_report.txt")])

        assert captured["names"] == ["my_report.txt"]

    def test_correct_business_key_passed_to_pipeline(self, client, ok_pipeline_result):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = ok_pipeline_result
            _upload(client, "solar_stay", [_txt_file()])

        MockPipeline.assert_called_once_with("solar_stay")

    def test_all_valid_keys_accepted(self, client, ok_pipeline_result):
        for key in ("luster", "solar_stay", "solar_gems"):
            with patch("api.main.DocumentUploadPipeline") as MockPipeline:
                MockPipeline.return_value.run.return_value = ok_pipeline_result
                resp = _upload(client, key, [_txt_file()])
            assert resp.status_code == 200, f"Failed for key: {key}"

    def test_partial_errors_still_200(self, client, error_pipeline_result):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = error_pipeline_result
            resp = _upload(client, "luster", [_txt_file()])

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert body["errors"][0]["file"] == "bad.txt"

    def test_csv_file_accepted(self, client, ok_pipeline_result):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = ok_pipeline_result
            resp = _upload(client, "luster", [_csv_file()])

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Invalid key — 400 errors
# ---------------------------------------------------------------------------

class TestUploadInvalidKey:

    def test_unknown_key_returns_400(self, client):
        resp = _upload(client, "unknown_biz", [_txt_file()])
        assert resp.status_code == 400

    def test_unknown_key_error_message(self, client):
        resp = _upload(client, "cafe", [_txt_file()])
        assert resp.status_code == 400
        assert "cafe" in resp.json()["detail"]

    def test_empty_key_returns_4xx(self, client):
        # FastAPI treats empty path segment as 404/405
        resp = client.post("/api/documents/upload/", files=[_txt_file()])
        assert resp.status_code in (404, 405, 307)


# ---------------------------------------------------------------------------
# Pipeline exception — 500 error
# ---------------------------------------------------------------------------

class TestUploadPipelineError:

    def test_pipeline_exception_returns_500(self, client):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = RuntimeError("Embedding service unavailable")
            resp = _upload(client, "luster", [_txt_file()])

        assert resp.status_code == 500

    def test_500_contains_error_detail(self, client):
        with patch("api.main.DocumentUploadPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = RuntimeError("DB write failed")
            resp = _upload(client, "luster", [_txt_file()])

        assert "DB write failed" in resp.json()["detail"]
