"""Business Intelligence Admin Dashboard — Home page.

Run with:
    streamlit run src/ui/app.py
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
    page_title="SOLAR Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom tile card CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    a.tile-card {
        display: block;
        text-decoration: none;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 2rem 1.5rem;
        text-align: center;
        background: #ffffff;
        transition: box-shadow 0.2s ease, transform 0.2s ease;
        cursor: pointer;
    }
    a.tile-card:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.12);
        transform: translateY(-3px);
        text-decoration: none;
    }
    a.tile-card .tile-icon {
        font-size: 3rem;
        line-height: 1;
        margin-bottom: 0.75rem;
    }
    a.tile-card .tile-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
        color: #111;
    }
    a.tile-card .tile-desc {
        font-size: 0.9rem;
        color: #555;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🏢 SOLAR Dashboard")
st.markdown("Select a section to get started.")
st.divider()

# ---------------------------------------------------------------------------
# Tile definitions  (href matches Streamlit's auto-generated page URLs)
# ---------------------------------------------------------------------------
TILES = [
    {
        "icon": "🤖",
        "title": "AI Agent",
        "desc": "Chat with the AI agent to query business insights and get answers.",
        "href": "/Chat",
    },
    {
        "icon": "📄",
        "title": "Documents",
        "desc": "Upload and index business documents to power the AI agent.",
        "href": "/Documents",
    },
]

# ---------------------------------------------------------------------------
# Render tiles — the entire card is a native <a> link, no extra button
# ---------------------------------------------------------------------------
cols = st.columns(len(TILES), gap="large")

for col, tile in zip(cols, TILES):
    with col:
        st.markdown(
            f"""
            <a class="tile-card" href="{tile['href']}" target="_self">
                <div class="tile-icon">{tile['icon']}</div>
                <div class="tile-title">{tile['title']}</div>
                <div class="tile-desc">{tile['desc']}</div>
            </a>
            """,
            unsafe_allow_html=True,
        )
