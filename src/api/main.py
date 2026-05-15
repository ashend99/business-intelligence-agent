"""FastAPI backend for the SOLAR BI Dashboard.

Exposes:
    POST   /api/chat
    GET    /api/documents/count/{business_key}
    POST   /api/documents/upload/{business_key}
    DELETE /api/documents/delete/{business_key}/{doc_name}
    DELETE /api/documents/delete/{business_key}          (body: {"doc_names": [...]})
    DELETE /api/documents/clear/{business_key}

Run with:
    uvicorn src.api.main:app --reload --port 8000
Or from the project root (with venv active):
    python -m uvicorn src.api.main:app --reload --port 8000
"""
import os
import re
import asyncio
import sys
import tempfile
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import build_agent  # noqa: E402
from ingestion.indexer import clear_collection, delete_document, drop_collection, get_collection_count, list_all_collections, list_documents, rename_collection  # noqa: E402
from ingestion.upload_docs import DocumentUploadPipeline  # noqa: E402
from ingestion.vectordb import get_vector_db  # noqa: E402

# PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = os.getenv("PROJECT_DIR") or Path(__file__).resolve().parent.parent.parent
_BUSINESS_CONFIG_PATH = Path(PROJECT_DIR) / "config" / "business_config.yaml"


def _load_business_keys() -> list[str]:
    with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [b["key"] for b in cfg["business"]["businesses"]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure all business collections exist in the vector DB at startup."""
    db = get_vector_db()
    for key in _load_business_keys():
        db.ensure_collection(key)
    yield


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="SOLAR BI API", version="1.0.0", redirect_slashes=True, lifespan=lifespan)

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

def _load_valid_keys() -> set[str]:
    with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as _f:
        _cfg = yaml.safe_load(_f)
    return {b["key"] for b in _cfg["business"]["businesses"]}

VALID_KEYS = _load_valid_keys()


_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')


def _validate_key(business_key: str) -> None:
    if business_key not in VALID_KEYS and not _SLUG_RE.match(business_key):
        raise HTTPException(status_code=400, detail=f"Invalid business_key: {business_key!r}. Must be a known key or a lowercase slug.")


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


@app.get("/api/collections")
async def get_collections() -> dict:
    """Return all collection names that exist in the vector DB."""
    try:
        return {"collections": list_all_collections()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
            # suffix = Path(f.filename or "file").suffix
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


class DeleteRequest(BaseModel):
    doc_names: list[str]


@app.delete("/api/documents/delete/{business_key}")
async def delete_docs_batch(business_key: str, req: DeleteRequest) -> dict:
    """Delete all chunks for multiple documents from a collection."""
    _validate_key(business_key)
    try:
        total = 0
        for name in req.doc_names:
            total += delete_document(business_key, name)
        return {"ok": True, "business_key": business_key, "doc_names": req.doc_names, "chunks_deleted": total}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/documents/delete/{business_key}/{doc_name}")
async def delete_doc(business_key: str, doc_name: str) -> dict:
    """Delete all chunks for a specific document from a collection."""
    _validate_key(business_key)
    try:
        deleted = delete_document(business_key, doc_name)
        return {"ok": True, "business_key": business_key, "doc_name": doc_name, "chunks_deleted": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/documents/clear/{business_key}")
async def clear_docs(business_key: str) -> dict:
    """Wipe and recreate the vector collection for a business."""
    _validate_key(business_key)
    try:
        clear_collection(business_key)
        return {"ok": True, "business_key": business_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Collection management (dynamic/custom collections only)
# ---------------------------------------------------------------------------

class RenameRequest(BaseModel):
    new_key: str


@app.delete("/api/collections/{collection_key}")
async def delete_collection_endpoint(collection_key: str) -> dict:
    """Delete an entire custom collection. Refuses pre-configured keys."""
    _validate_key(collection_key)
    if collection_key in VALID_KEYS:
        raise HTTPException(status_code=400, detail=f"Cannot delete a pre-configured collection: {collection_key!r}")
    try:
        drop_collection(collection_key)
        return {"ok": True, "deleted": collection_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/collections/{collection_key}/rename")
async def rename_collection_endpoint(collection_key: str, req: RenameRequest) -> dict:
    """Rename a custom collection. Refuses pre-configured keys."""
    _validate_key(collection_key)
    if collection_key in VALID_KEYS:
        raise HTTPException(status_code=400, detail=f"Cannot rename a pre-configured collection: {collection_key!r}")
    new_key = req.new_key.strip().lower().replace(" ", "_")
    if not _SLUG_RE.match(new_key):
        raise HTTPException(status_code=400, detail=f"Invalid collection name: {new_key!r}. Must be lowercase slug.")
    if new_key == collection_key:
        return {"ok": True, "old_key": collection_key, "new_key": new_key}
    try:
        rename_collection(collection_key, new_key)
        return {"ok": True, "old_key": collection_key, "new_key": new_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
