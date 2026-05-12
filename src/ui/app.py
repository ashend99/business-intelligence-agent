"""Business Intelligence Admin Dashboard — entry point.

Run with:
    streamlit run src/ui/app.py

The sidebar business selector is the global context. All pages read
st.session_state.business_key to know which business they are operating on.
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BI Admin Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Business selector (global — persists across pages via session state)
# ---------------------------------------------------------------------------
BUSINESSES = {
    "cafe": "☕ Café & Restaurant",
    "hotel": "🏨 Airport Hotel",
    "gems": "💎 Gem & Jewellery",
}

st.sidebar.title("🏢 BI Dashboard")
st.sidebar.markdown("---")

previous_key = st.session_state.get("business_key", "cafe")

selected_label = st.sidebar.radio(
    "Select Business",
    options=list(BUSINESSES.values()),
    index=list(BUSINESSES.keys()).index(previous_key),
)

# Resolve label → key
selected_key = next(k for k, v in BUSINESSES.items() if v == selected_label)

# Reset chat state when the business changes
if selected_key != previous_key:
    st.session_state.business_key = selected_key
    st.session_state.pop("agent", None)
    st.session_state.pop("thread_id", None)
    st.session_state.pop("messages", None)
else:
    st.session_state.business_key = selected_key

st.sidebar.markdown("---")
st.sidebar.caption("Navigate using the pages in the sidebar above.")

# ---------------------------------------------------------------------------
# Landing page content
# ---------------------------------------------------------------------------
st.title(f"Welcome, {BUSINESSES[selected_key]}")
st.markdown(
    """
    Use the **sidebar** to navigate between sections:

    | Page | Description |
    |------|-------------|
    | 💬 Chat | Ask questions about this business using the AI agent |
    | 📄 Documents | Upload and index business documents |

    Select a business above to switch context. The chat history and indexed
    documents are scoped to the selected business.
    """
)
