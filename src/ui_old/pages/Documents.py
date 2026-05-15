"""Documents page — upload, index, and manage business documents."""

import sys
from pathlib import Path

import streamlit as st

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ingestion.indexer import clear_collection, get_collection_count  # noqa: E402
from ingestion.upload_docs import DocumentUploadPipeline  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Documents",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

BUSINESSES = {
    "cafe": "☕ Café & Restaurant",
    "hotel": "🏨 Airport Hotel",
    "gems": "💎 Gem & Jewellery",
}

SUPPORTED_TYPES = ["pdf", "docx", "xlsx", "csv", "txt"]

# ---------------------------------------------------------------------------
# Read global business context
# ---------------------------------------------------------------------------
business_key: str = st.session_state.get("business_key", "cafe")
business_label: str = BUSINESSES[business_key]

st.title(f"📄 Documents — {business_label}")
st.caption("Upload documents to make them searchable by the AI agent.")

# ---------------------------------------------------------------------------
# Collection stats
# ---------------------------------------------------------------------------
st.subheader("Collection Status")

try:
    count = get_collection_count(business_key)
    col1, col2 = st.columns(2)
    col1.metric("Indexed Chunks", count)
    col2.metric("Business", business_key)
except Exception as exc:
    st.error(f"Could not connect to vector store: {exc}")
    st.stop()

st.divider()

# ---------------------------------------------------------------------------
# Upload & Index
# ---------------------------------------------------------------------------
st.subheader("Upload & Index Documents")

uploaded_files = st.file_uploader(
    "Choose files to index",
    type=SUPPORTED_TYPES,
    accept_multiple_files=True,
    help="Supported formats: PDF, DOCX, XLSX, CSV, TXT",
)

if uploaded_files:
    if st.button("⚡ Index uploaded files", type="primary"):
        # Write uploads to temp files so the pipeline can read them by path
        tmp_paths: list[tuple[Path, str]] = []
        for uploaded_file in uploaded_files:
            import tempfile
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_paths.append((Path(tmp.name), uploaded_file.name))

        file_paths = [p for p, _ in tmp_paths]
        name_map = {p: name for p, name in tmp_paths}

        progress = st.progress(0, text="Starting…")

        pipeline = DocumentUploadPipeline(business_key)
        result = pipeline.run(file_paths)

        progress.progress(1.0, text="Done.")

        # Clean up temp files
        for path in file_paths:
            path.unlink(missing_ok=True)

        if result.errors:
            st.warning(
                f"Indexed {result.chunks_indexed} chunks from "
                f"{result.files_processed} file(s). "
                f"{len(result.errors)} file(s) had errors:"
            )
            for err in result.errors:
                st.error(f"{err['file']}: {err['error']}")
        else:
            st.success(
                f"Successfully indexed {result.chunks_indexed} chunks from "
                f"{result.files_processed} file(s)."
            )
            st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Danger zone — clear collection
# ---------------------------------------------------------------------------
st.subheader("⚠️ Danger Zone")

with st.expander("Clear all indexed documents for this business"):
    st.warning(
        f"This will permanently delete all {count} indexed chunks for "
        f"**{business_label}**. This cannot be undone."
    )
    confirm = st.text_input(
        f'Type **{business_key}** to confirm',
        placeholder=business_key,
    )
    if st.button("🗑️ Clear collection", type="secondary", disabled=(confirm != business_key)):
        try:
            clear_collection(business_key)
            st.success("Collection cleared successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to clear collection: {exc}")
