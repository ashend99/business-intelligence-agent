"""FastAPI backend for the SOLAR BI Dashboard.

Exposes:
    POST   /api/chat
    GET    /api/documents/count/{business_key}
    POST   /api/documents/upload/{business_key}
    DELETE /api/documents/clear/{business_key}

Run with:
    uvicorn src.api.main:app --reload --port 8000
Or from the project root (with venv active):
    python -m uvicorn src.api.main:app --reload --port 8000
"""
import os
import asyncio
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import build_agent  # noqa: E402
from ingestion.indexer import clear_collection, get_collection_count, list_documents  # noqa: E402
from ingestion.upload_docs import DocumentUploadPipeline  # noqa: E402

PROJECT_DIR = str(os.getenv("PROJECT_DIR"))

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="SOLAR BI API", version="1.0.0", redirect_slashes=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)

# Cache one agent per business_key (they hold MemorySaver internally)
_agents: dict[str, object] = {}


def _get_agent(business_key: str) -> object:
    if business_key not in _agents:
        _agents[business_key] = build_agent(business_key)
    return _agents[business_key]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

_BUSINESS_CONFIG_PATH = Path(PROJECT_DIR) / "config" / "business_config.yaml"

def _load_valid_keys() -> set[str]:
    with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as _f:
        _cfg = yaml.safe_load(_f)
    return {b["key"] for b in _cfg["business"]["businesses"]}

VALID_KEYS = _load_valid_keys()


def _validate_key(business_key: str) -> None:
    if business_key not in VALID_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown business_key: {business_key!r}")


class ChatRequest(BaseModel):
    business_key: str
    thread_id: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config")
async def get_config() -> dict:
    """Return the business configuration from business_config.yaml."""
    try:
        with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    """Invoke the LangGraph agent and return the assistant reply."""
    _validate_key(req.business_key)

    agent = _get_agent(req.business_key)
    loop = asyncio.get_event_loop()

    try:
        result = await loop.run_in_executor(
            _executor,
            lambda: agent.invoke(
                {"messages": [{"role": "user", "content": req.message}]},
                config={"configurable": {"thread_id": req.thread_id}},
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    answer: str = result["messages"][-1].content
    return {"answer": answer}


@app.get("/api/documents/list/{business_key}")
async def doc_list(business_key: str) -> dict:
    """Return per-file document names and chunk counts for a collection."""
    _validate_key(business_key)
    try:
        docs = list_documents(business_key)
        return {"business_key": business_key, "documents": docs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/documents/count/{business_key}")
async def doc_count(business_key: str) -> dict:
    """Return the number of indexed chunks for a business collection."""
    _validate_key(business_key)
    try:
        count = get_collection_count(business_key)
        return {"business_key": business_key, "count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/documents/upload/{business_key}")
async def upload_docs(
    business_key: str,
    files: list[UploadFile] = File(...),
) -> dict:
    """
    Upload one or more files and run the ingestion pipeline.

    Args:
        business_key: The business collection to index into.
        files: List of files to upload (multipart/form-data).
    Returns:
        Dict with counts of processed files, indexed chunks, and any errors.
    """
    _validate_key(business_key)

    tmp_paths: list[Path] = []
    try:
        for f in files:
            suffix = Path(f.filename or "file").suffix
            original_name = Path(f.filename or "file").name
            tmp_dir = Path(tempfile.mkdtemp())
            tmp_path = tmp_dir / original_name
            tmp_path.write_bytes(await f.read())
            tmp_paths.append(tmp_path)

        loop = asyncio.get_event_loop()
        pipeline = DocumentUploadPipeline(business_key)
        result = await loop.run_in_executor(
            _executor,
            lambda: pipeline.run(tmp_paths),
        )

        return {
            "files_processed": result.files_processed,
            "chunks_indexed": result.chunks_indexed,
            "errors": result.errors,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)
            try:
                p.parent.rmdir()
            except OSError:
                pass


@app.delete("/api/documents/clear/{business_key}")
async def clear_docs(business_key: str) -> dict:
    """Wipe and recreate the vector collection for a business."""
    _validate_key(business_key)
    try:
        clear_collection(business_key)
        return {"ok": True, "business_key": business_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
