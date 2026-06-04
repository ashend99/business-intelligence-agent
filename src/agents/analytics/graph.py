"""Analytics sub-agent — answers social media analytics questions via the MCP server.

Connects to the Social Analytics MCP server (src/mcp_server/server.py) on each
invocation and loads all available tools via MCP. The MCP server must be running
(python -m mcp_server.server) before this agent is invoked.

Public API:
    invoke_analytics_agent(messages, business_key, runtime_context=None) -> (str, list[dict])
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents.prompts import get_agent_prompt
from agents.state import extract_reasoning_steps
from config.settings import settings

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_MCP_SERVER_URL = "http://localhost:8001"


def _get_analytics_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.analytics_model,
        temperature=settings.analytics_temperature,
        max_tokens=settings.analytics_max_tokens,
        api_key=settings.openai_api_key,
    )


async def _ainvoke(
    messages: list[dict],
    runtime_context: str | None,
) -> tuple[str, list[dict]]:
    client = MultiServerMCPClient({
        "social-analytics": {
            "url": f"{_MCP_SERVER_URL}/mcp/",
            "transport": "streamable_http",
        }
    })
    tools = await client.get_tools()
    system_prompt = get_agent_prompt("analytics")
    agent = create_react_agent(
        model=_get_analytics_llm(),
        tools=tools,
        prompt=system_prompt,
    )
    model_messages = (
        [{"role": "system", "content": runtime_context}] if runtime_context else []
    ) + messages
    result = await agent.ainvoke({"messages": model_messages})
    steps = extract_reasoning_steps(result["messages"])
    return result["messages"][-1].content, steps


def invoke_analytics_agent(
    messages: list[dict[str, str]],
    business_key: str,
    runtime_context: str | None = None,
) -> tuple[str, list[dict]]:
    """Invoke the analytics agent for a single turn.

    Returns:
        (answer, reasoning_steps) where reasoning_steps contains the tool
        calls and tool results from the ReAct loop.
    """
    def _run() -> tuple[str, list[dict]]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_ainvoke(messages, runtime_context))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    logger.info("Analytics agent invoked for business_key=%s", business_key)
    return _EXECUTOR.submit(_run).result()
