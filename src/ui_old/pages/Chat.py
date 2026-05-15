"""Chat page — AI agent conversation scoped to the selected business."""

import sys
import uuid
from pathlib import Path

import streamlit as st

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agent.graph import build_agent  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

BUSINESSES = {
    "cafe": "☕ Café & Restaurant",
    "hotel": "🏨 Airport Hotel",
    "gems": "💎 Gem & Jewellery",
}

# ---------------------------------------------------------------------------
# Read global business context
# ---------------------------------------------------------------------------
business_key: str = st.session_state.get("business_key", "cafe")
business_label: str = BUSINESSES[business_key]

st.title(f"💬 Chat — {business_label}")
st.caption(
    "Ask questions about this business. "
    "The agent searches indexed documents and cites its sources."
)

# ---------------------------------------------------------------------------
# Initialise per-session agent state
# ---------------------------------------------------------------------------
if "agent" not in st.session_state or "thread_id" not in st.session_state:
    with st.spinner("Loading agent…"):
        st.session_state.agent = build_agent(business_key)
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []

agent = st.session_state.agent
thread_id: str = st.session_state.thread_id

# ---------------------------------------------------------------------------
# Render chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Handle new user input
# ---------------------------------------------------------------------------
if prompt := st.chat_input("Ask something about this business…"):
    # Display user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Invoke agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config={"configurable": {"thread_id": thread_id}},
                )
                answer: str = result["messages"][-1].content
            except Exception as exc:  # noqa: BLE001
                answer = f"⚠️ An error occurred: {exc}"

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

# ---------------------------------------------------------------------------
# Sidebar: session controls
# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Session")
st.sidebar.caption(f"Business: **{business_label}**")
st.sidebar.caption(f"Thread ID: `{thread_id[:8]}…`")

if st.sidebar.button("🗑️ Clear conversation"):
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()
