"""LangGraph agent for the business intelligence chatbot.

A single shared agent searches across all business collections.
Conversation state is persisted via SqliteSaver (vectorstore/checkpoints.db).

Usage:
    from agent.graph import get_agent

    agent = get_agent()
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "What are our top products?"}]},
        config={"configurable": {"thread_id": "session-abc123"}},
    )
    print(response["messages"][-1].content)
"""

import sqlite3
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

from agent.prompts import get_system_prompt
from config.settings import settings
from tools.rag_tool import build_rag_tool

# Shared SQLite checkpointer — persists all threads across server restarts.
_CHECKPOINT_DB = settings.chroma_persist_dir.parent / "checkpoints.db"
_CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
_conn = sqlite3.connect(str(_CHECKPOINT_DB), check_same_thread=False)
_checkpointer = SqliteSaver(_conn)

# Single compiled agent instance shared across all requests.
_agent = None


def get_agent() -> object:
    """Return the singleton agent, building it on first call."""
    global _agent
    if _agent is None:
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.openai_api_key,
        )
        rag_tool = build_rag_tool()
        system_prompt = get_system_prompt()
        _agent = create_react_agent(
            model=llm,
            tools=[rag_tool],
            prompt=system_prompt,
            checkpointer=_checkpointer,
        )
    return _agent


# Keep build_agent as a compatibility shim so existing imports don't break.
def build_agent(business_key: str = "") -> object:
    return get_agent()
