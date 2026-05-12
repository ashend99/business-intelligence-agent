"""LangGraph agent for the business intelligence chatbot.

Uses create_react_agent with:
- GPT-4o as the LLM
- build_rag_tool(business_key) as the only tool (scoped to one collection)
- MemorySaver checkpointer for session-based conversation memory
- A versioned system prompt loaded from config/prompts/

Usage:
    from agent.graph import build_agent

    agent = build_agent("cafe")
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "What's on the menu?"}]},
        config={"configurable": {"thread_id": "session-abc123"}},
    )
    print(response["messages"][-1].content)
"""

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from agent.prompts import get_system_prompt
from config.settings import settings
from tools.rag_tool import build_rag_tool


def build_agent(business_key: str) -> object:
    """Build and return a ReAct agent scoped to a single business.

    The agent shares one MemorySaver instance per call, so conversation
    history is maintained across turns as long as the same thread_id is
    passed in the config. Each new Streamlit session should use a unique
    thread_id (e.g. str(uuid.uuid4())).

    Args:
        business_key: One of "cafe", "hotel", or "gems".

    Returns:
        A compiled LangGraph CompiledGraph ready to invoke.

    Raises:
        KeyError: If business_key is not a known collection (from build_rag_tool).
        FileNotFoundError: If the configured prompt file is missing.
    """
    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key,
    )

    rag_tool = build_rag_tool(business_key)
    system_prompt = get_system_prompt()
    checkpointer = MemorySaver()

    return create_react_agent(
        model=llm,
        tools=[rag_tool],
        prompt=system_prompt,
        checkpointer=checkpointer,
    )
