"""Supervisor agent for the business intelligence chatbot.

Uses a Supervisor planner to decide whether to run the RAG agent and/or the
Analytics agent, then merges selected outputs into a polished final answer.

Graph flow:
        supervisor (decide flags)
            ├─ call_rag_agent
            ├─ call_analytics_agent
            └─ synthesize

        call_rag_agent / call_analytics_agent may route to the other execution
        node (for mixed queries) or directly to synthesize.

The SQLite checkpointer persists the full OrchestratorState per thread_id,
giving the supervisor multi-turn memory. Sub-agents are stateless per turn.

Usage:
    from agents.graph import get_agent

    agent = get_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What are our opening hours?"}],
         "business_key": "cafe"},
        config={"configurable": {"thread_id": "session-abc123"}},
    )
    print(result["final_answer"])
"""

import logging
import sqlite3
import json
from datetime import datetime

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.constants import END
from langgraph.graph import StateGraph

from agents.state import OrchestratorState
from config.settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Checkpointer (orchestrator-level only)
# ---------------------------------------------------------------------------
_CHECKPOINT_DB = settings.chroma_persist_dir.parent / "checkpoints.db"
_CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
_conn = sqlite3.connect(str(_CHECKPOINT_DB), check_same_thread=False)
_checkpointer = SqliteSaver(_conn)

_graph = None
_orchestrator_llm: ChatOpenAI | None = None


def _get_orchestrator_llm() -> ChatOpenAI:
    global _orchestrator_llm
    if _orchestrator_llm is None:
        _orchestrator_llm = ChatOpenAI(
            model=settings.orchestrator_model,
            temperature=settings.orchestrator_temperature,
            max_tokens=settings.orchestrator_max_tokens,
            api_key=settings.openai_api_key,
        )
    return _orchestrator_llm


def _parse_supervisor_flags(raw: str) -> tuple[bool, bool]:
    """Parse supervisor decision JSON into execution flags.

    Expected shape:
        {"run_rag_agent": true|false, "run_analytical_agent": true|false}
    """
    try:
        data = json.loads((raw or "").strip())
        run_rag = bool(data.get("run_rag_agent", True))
        run_analytical = bool(data.get("run_analytical_agent", True))
        return run_rag, run_analytical
    except Exception:
        # Safe fallback: execute both so the user still gets coverage.
        return True, True


def _append_sub_agent_output(existing: str | None, section: str, content: str) -> str:
    """Append one tagged sub-agent output block to the aggregate payload."""
    block = f"[{section}]\n{content.strip() if content else f'No {section.lower()} output.'}"
    if existing:
        return f"{existing}\n\n{block}"
    return block


def _state_history_to_role_messages(state: OrchestratorState) -> list[dict[str, str]]:
    """Convert persisted state messages into OpenAI-compatible role messages."""
    history: list[dict[str, str]] = []
    for msg in state.get("messages") or []:
        role = None
        content = None

        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")
        else:
            msg_type = getattr(msg, "type", "")
            if msg_type in ("human", "user"):
                role = "user"
            elif msg_type in ("ai", "assistant"):
                role = "assistant"
            elif msg_type == "system":
                role = "system"
            content = getattr(msg, "content", None)

        if role in ("user", "assistant", "system") and isinstance(content, str) and content.strip():
            history.append({"role": role, "content": content})

    return history


def _latest_user_message(history: list[dict[str, str]]) -> str:
    """Return the latest user message content from role-message history."""
    for msg in reversed(history):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _runtime_context_text(state: OrchestratorState) -> str:
    """Build a compact runtime context block for relative-date reasoning."""
    current_datetime = state.get("current_datetime") or datetime.now().astimezone().isoformat()
    current_timezone = state.get("current_timezone") or (datetime.now().astimezone().tzname() or "local")
    return (
        "Runtime context:\n"
        f"- current_datetime: {current_datetime}\n"
        f"- current_timezone: {current_timezone}\n"
        "Use this context to interpret relative dates like yesterday, last week, or this month."
    )


# ---------------------------------------------------------------------------
# Node: supervisor
# ---------------------------------------------------------------------------

def supervisor(state: OrchestratorState) -> dict:
    """Decide which isolated sub-agents should run."""
    from agents.prompts import get_agent_prompt

    history_messages = _state_history_to_role_messages(state)
    runtime_context = _runtime_context_text(state)

    llm = _get_orchestrator_llm()
    decision_prompt = get_agent_prompt("orchestrator")
    decision_response = llm.invoke([
        {"role": "system", "content": f"{decision_prompt}\n\n{runtime_context}"},
        *history_messages,
    ])
    print(f"Supervisor decision response: {decision_response.content}")
    run_rag_agent, run_analytical_agent = _parse_supervisor_flags(decision_response.content)

    reasoning_steps: list[dict] = [
        {
            "type": "supervisor",
            "content": (
                f"run_rag_agent={str(run_rag_agent).lower()}, "
                f"run_analytical_agent={str(run_analytical_agent).lower()}"
            ),
        }
    ]

    return {
        "current_datetime": state.get("current_datetime"),
        "current_timezone": state.get("current_timezone"),
        "run_rag_agent": run_rag_agent,
        "run_analytical_agent": run_analytical_agent,
        "sub_agent_result": None,
        "rag_executed": False,
        "analytics_executed": False,
        "reasoning_steps": reasoning_steps,
    }


# ---------------------------------------------------------------------------
# Node: call_rag_agent
# ---------------------------------------------------------------------------

def call_rag_agent(state: OrchestratorState) -> dict:
    """Invoke the isolated RAG sub-agent and append its output."""
    from agents.rag.graph import invoke_rag_agent

    history_messages = _state_history_to_role_messages(state)
    reasoning_steps = state.get("reasoning_steps") or []
    runtime_context = _runtime_context_text(state)

    try:
        answer, steps = invoke_rag_agent(history_messages, state["business_key"], runtime_context=runtime_context)
        return {
            "sub_agent_result": _append_sub_agent_output(state.get("sub_agent_result"), "RAG", answer),
            "rag_executed": True,
            "reasoning_steps": reasoning_steps + steps,
        }
    except Exception as exc:
        logger.exception("RAG sub-agent failed")
        return {
            "sub_agent_result": _append_sub_agent_output(
                state.get("sub_agent_result"), "RAG", f"RAG error: {exc}"
            ),
            "rag_executed": True,
            "reasoning_steps": reasoning_steps + [{"type": "agent_error", "tool": "rag", "content": str(exc)}],
        }


# ---------------------------------------------------------------------------
# Node: call_analytics_agent
# ---------------------------------------------------------------------------

def call_analytics_agent(state: OrchestratorState) -> dict:
    """Invoke the isolated Analytics sub-agent and append its output."""
    from agents.analytics.graph import invoke_analytics_agent

    history_messages = _state_history_to_role_messages(state)
    reasoning_steps = state.get("reasoning_steps") or []
    runtime_context = _runtime_context_text(state)

    try:
        answer, steps = invoke_analytics_agent(history_messages, state["business_key"], runtime_context=runtime_context)
        return {
            "sub_agent_result": _append_sub_agent_output(state.get("sub_agent_result"), "ANALYTICS", answer),
            "analytics_executed": True,
            "reasoning_steps": reasoning_steps + steps,
        }
    except Exception as exc:
        logger.exception("Analytics sub-agent failed")
        return {
            "sub_agent_result": _append_sub_agent_output(
                state.get("sub_agent_result"), "ANALYTICS", f"Analytics error: {exc}"
            ),
            "analytics_executed": True,
            "reasoning_steps": reasoning_steps + [{"type": "agent_error", "tool": "analytics", "content": str(exc)}],
        }


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def route_from_supervisor(state: OrchestratorState) -> str:
    """Pick the first execution node (or synthesize when both are skipped)."""
    if state.get("run_rag_agent", False):
        return "call_rag_agent"
    if state.get("run_analytical_agent", False):
        return "call_analytics_agent"
    return "synthesize"


def route_after_rag(state: OrchestratorState) -> str:
    """After RAG, run analytics if selected and not executed yet."""
    if state.get("run_analytical_agent", False) and not state.get("analytics_executed", False):
        return "call_analytics_agent"
    return "synthesize"


def route_after_analytics(state: OrchestratorState) -> str:
    """After analytics, run RAG if selected and not executed yet."""
    if state.get("run_rag_agent", False) and not state.get("rag_executed", False):
        return "call_rag_agent"
    return "synthesize"


# ---------------------------------------------------------------------------
# Node: synthesize
# ---------------------------------------------------------------------------

def synthesize(state: OrchestratorState) -> dict:
    """Rewrite aggregated sub-agent outputs into a polished final answer."""
    from agents.prompts import get_agent_prompt

    llm = _get_orchestrator_llm()
    system_prompt = get_agent_prompt("synthesizer")
    history_messages = _state_history_to_role_messages(state)
    runtime_context = _runtime_context_text(state)
    user_question = _latest_user_message(history_messages)
    sub_result = state.get("sub_agent_result") or ""

    human_content = (
        f"Latest user question: {user_question}\n\n"
        f"Sub-agent response:\n{sub_result}"
    )
    response = llm.invoke([
        {"role": "system", "content": f"{system_prompt}\n\n{runtime_context}"},
        *history_messages,
        {"role": "user", "content": human_content},
    ])
    final_text = response.content.strip()
    return {
        "final_answer": final_text,
        "messages": [AIMessage(content=final_text)],
    }


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _build_graph():
    graph = StateGraph(OrchestratorState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("call_rag_agent", call_rag_agent)
    graph.add_node("call_analytics_agent", call_analytics_agent)
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "call_rag_agent": "call_rag_agent",
            "call_analytics_agent": "call_analytics_agent",
            "synthesize": "synthesize",
        },
    )
    graph.add_conditional_edges(
        "call_rag_agent",
        route_after_rag,
        {
            "call_analytics_agent": "call_analytics_agent",
            "synthesize": "synthesize",
        },
    )
    graph.add_conditional_edges(
        "call_analytics_agent",
        route_after_analytics,
        {
            "call_rag_agent": "call_rag_agent",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("synthesize", END)

    return graph.compile(checkpointer=_checkpointer)


def get_agent():
    """Return the compiled orchestrator graph, building it on first call."""
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def build_agent(business_key: str = ""):
    """Compatibility shim — returns the singleton orchestrator graph."""
    return get_agent()
