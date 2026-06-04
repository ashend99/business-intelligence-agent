"""Chat page — AI agent conversation scoped to the selected business."""

import sys
import uuid
from pathlib import Path

import streamlit as st

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.graph import build_agent  # noqa: E402

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

if "show_reasoning" not in st.session_state:
    st.session_state.show_reasoning = False

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
                    {
                        "messages": [{"role": "user", "content": prompt}],
                        "business_key": business_key,
                    },
                    config={"configurable": {"thread_id": thread_id}},
                )
                answer: str = result.get("final_answer") or result["messages"][-1].content
                reasoning: list = result.get("reasoning_steps") or []
            except Exception as exc:  # noqa: BLE001
                answer = f"⚠️ An error occurred: {exc}"
                reasoning = []

        st.markdown(answer)

        if st.session_state.show_reasoning and reasoning:
            with st.expander("Reasoning steps", expanded=False):
                for step in reasoning:
                    if step["type"] == "intent":
                        st.markdown(f"**Intent classified:** `{step['content']}`")
                    elif step["type"] == "tool_call":
                        st.markdown(f"**Tool called:** `{step['tool']}`")
                        st.code(step.get("input", ""), language="json")
                    elif step["type"] == "tool_result":
                        st.markdown(f"**Result from:** `{step['tool']}`")
                        st.code(step.get("content", ""), language="json")

        st.session_state.messages.append({"role": "assistant", "content": answer})

# ---------------------------------------------------------------------------
# Sidebar: session controls
# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Session")
st.sidebar.caption(f"Business: **{business_label}**")
st.sidebar.caption(f"Thread ID: `{thread_id[:8]}…`")

st.sidebar.markdown("---")
st.sidebar.subheader("Debug")
st.session_state.show_reasoning = st.sidebar.checkbox(
    "Show reasoning steps",
    value=st.session_state.show_reasoning,
)

if st.sidebar.button("🗑️ Clear conversation"):
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()
