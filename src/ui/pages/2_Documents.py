"""Documents page — upload, index, and manage business documents."""

import sys
import tempfile
from pathlib import Path

import streamlit as st

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ingestion.indexer import clear_collection, get_collection_count, index_documents  # noqa: E402
from ingestion.loader import load_document  # noqa: E402
from ingestion.splitter import split_documents  # noqa: E402

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
        total_chunks = 0
        errors = []

        progress = st.progress(0, text="Starting…")

        for i, uploaded_file in enumerate(uploaded_files):
            progress.progress(
                (i) / len(uploaded_files),
                text=f"Processing {uploaded_file.name}…",
            )
            try:
                # Write to a temp file so loader can read it by path
                suffix = Path(uploaded_file.name).suffix
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    tmp_path = Path(tmp.name)

                docs = load_document(tmp_path)
                # Preserve original filename in metadata
                for doc in docs:
                    doc.metadata["source"] = uploaded_file.name

                chunks = split_documents(docs)
                indexed = index_documents(chunks, business_key)
                total_chunks += indexed

            except Exception as exc:  # noqa: BLE001
                errors.append(f"{uploaded_file.name}: {exc}")
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        progress.progress(1.0, text="Done.")

        if errors:
            st.warning(f"Indexed {total_chunks} chunks. Some files had errors:")
            for err in errors:
                st.error(err)
        else:
            st.success(
                f"Successfully indexed {total_chunks} chunks from "
                f"{len(uploaded_files)} file(s)."
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
