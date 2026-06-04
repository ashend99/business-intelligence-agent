"""RAG sub-agent — searches the knowledge base and answers document-based questions.

This agent is stateless (no checkpointer). It is invoked fresh each turn by the
orchestrator. Multi-turn memory is managed at orchestrator level.

Public API:
    invoke_rag_agent(messages, business_key, runtime_context=None) -> str
        Call from the orchestrator's call_rag_agent node.
"""

import logging

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents.prompts import get_agent_prompt
from agents.state import extract_reasoning_steps
from config.settings import settings
from tools.rag_tool import build_rag_tool

logger = logging.getLogger(__name__)

_rag_agent = None


def _get_rag_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.rag_model,
        temperature=settings.rag_temperature,
        max_tokens=settings.rag_max_tokens,
        api_key=settings.openai_api_key,
    )


def _build_rag_agent():
    rag_tool = build_rag_tool()
    system_prompt = get_agent_prompt("rag")
    return create_react_agent(
        model=_get_rag_llm(),
        tools=[rag_tool],
        prompt=system_prompt,
    )


def invoke_rag_agent(
    messages: list[dict[str, str]],
    business_key: str,
    runtime_context: str | None = None,
) -> tuple[str, list[dict]]:
    """Invoke the RAG agent for a single turn.

    Returns:
        (answer, reasoning_steps) where reasoning_steps contains the tool
        calls and tool results from the ReAct loop.
    """
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = _build_rag_agent()

    logger.info("RAG agent invoked for business_key=%s", business_key)
    model_messages = ([{"role": "system", "content": runtime_context}] if runtime_context else []) + messages
    result = _rag_agent.invoke(
        {"messages": model_messages},
    )
    steps = extract_reasoning_steps(result["messages"])
    return result["messages"][-1].content, steps
