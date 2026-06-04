"""Shared state TypedDicts for the multi-agent graph."""

from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph.message import add_messages


def extract_reasoning_steps(messages: list) -> list[dict]:
    """Extract tool-call and tool-result steps from a ReAct agent message list.

    Skips the first HumanMessage and the final AIMessage (the answer).
    Returns a list of dicts with keys: type, tool, input / content.
    """
    steps = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                steps.append({
                    "type": "tool_call",
                    "tool": tc["name"],
                    "input": str(tc.get("args", {})),
                })
        elif isinstance(msg, ToolMessage):
            content = msg.content
            if isinstance(content, str) and len(content) > 500:
                content = content[:500] + "…"
            steps.append({
                "type": "tool_result",
                "tool": getattr(msg, "name", "") or "",
                "content": content,
            })
    return steps


class OrchestratorState(TypedDict):
    """Persistent state for the orchestrator graph (stored per thread_id)."""
    messages: Annotated[list[BaseMessage], add_messages]
    business_key: str
    current_datetime: NotRequired[str]
    current_timezone: NotRequired[str]
    run_rag_agent: NotRequired[bool]
    run_analytical_agent: NotRequired[bool]
    rag_executed: NotRequired[bool]
    analytics_executed: NotRequired[bool]
    sub_agent_result: str | None       # raw output from the sub-agent
    final_answer: str | None           # synthesized answer sent to the user
    reasoning_steps: list[dict] | None # per-turn reasoning trace (reset each turn)


class RAGAgentState(TypedDict):
    """Ephemeral state for the RAG sub-agent (no checkpointer)."""
    messages: Annotated[list[BaseMessage], add_messages]
    business_key: str


class AnalyticsAgentState(TypedDict):
    """Ephemeral state for the Analytics sub-agent (no checkpointer)."""
    messages: Annotated[list[BaseMessage], add_messages]
    business_key: str
