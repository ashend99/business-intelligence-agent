# Multi-Agent Architecture Plan

## Context

The current system uses a single LangGraph `create_react_agent` with one `search_documents` tool. Social analytics logic lives directly in `main.py` as raw API calls. The goal is to promote this into a proper multi-agent system: an orchestrator that routes to purpose-built RAG and Analytics sub-agents, each with their own reasoning loop, model, and prompt. The orchestrator synthesizes the final answer. This lays the foundation for adding more agents later (web search, report generation, etc.).

---

## Target Architecture

```
POST /api/chat
    ↓
Orchestrator Agent  (gpt-4o)
    ├── classify_intent
    ├── "rag"       → RAG Agent (gpt-4o-mini) → synthesize → END
    ├── "analytics" → Analytics Agent (gpt-4o-mini) → synthesize → END
    └── "general"   → direct_response → END
```

- Sequential routing only (no parallel calls)
- Single SQLite checkpointer at orchestrator level; sub-agents are ephemeral per-turn
- Orchestrator synthesizes sub-agent output into the final user-facing answer
- Sub-agents invoked as plain Python function calls inside orchestrator node functions (avoids LangGraph state schema compatibility issues)

---

## New Folder Structure

```
src/agents/
    graph.py           ← REPLACE entirely (orchestrator)
    prompts.py         ← EXTEND with get_agent_prompt()
    state.py           ← NEW
    rag/
        __init__.py    ← NEW (empty)
        graph.py       ← NEW
    analytics/
        __init__.py    ← NEW (empty)
        graph.py       ← NEW
        tools.py       ← NEW

config/prompts/
    system_v1.txt      ← existing (untouched)
    orchestrator_v1.txt ← NEW
    synthesizer_v1.txt  ← NEW
    rag_v1.txt          ← NEW
    analytics_v1.txt    ← NEW
    direct_response_v1.txt ← NEW
```

---

## Step-by-Step Implementation

### Step 1 — Foundation (no breakage)

**`config/config.yaml`** — add under existing keys:
```yaml
agents:
  orchestrator:
    model: "gpt-4o"
    temperature: 0.0
    max_tokens: 1024
    prompt_version: "v1"
  rag:
    model: "gpt-4o-mini"
    temperature: 0.0
    max_tokens: 2048
    prompt_version: "v1"
  analytics:
    model: "gpt-4o-mini"
    temperature: 0.0
    max_tokens: 2048
    prompt_version: "v1"
  synthesizer:
    prompt_version: "v1"
  direct_response:
    prompt_version: "v1"
```

**`src/config/settings.py`** — after the existing `agent` block, add reading of `agents` block:
- `self.orchestrator_model`, `self.orchestrator_temperature`, `self.orchestrator_max_tokens`
- `self.rag_model`, `self.rag_temperature`, `self.rag_max_tokens`
- `self.analytics_model`, `self.analytics_temperature`, `self.analytics_max_tokens`
- `self.agent_prompt_versions: dict` — keys: `orchestrator`, `rag`, `analytics`, `synthesizer`, `direct_response`; values from config, defaulting to `"v1"`

**`src/agents/prompts.py`** — keep `get_system_prompt()` unchanged. Add:
```python
def get_agent_prompt(agent_name: str, version: str | None = None) -> str
```
Resolves `version` from `settings.agent_prompt_versions[agent_name]` if not provided. Path: `settings.prompts_dir / f"{agent_name}_{version}.txt"`. Raises `FileNotFoundError` with a clear message.

**`src/agents/state.py`** — new file with three TypedDicts:

`OrchestratorState`:
- `messages: Annotated[list[BaseMessage], add_messages]` — full conversation history with `add_messages` reducer
- `business_key: str`
- `intent: str` — `"rag"` | `"analytics"` | `"general"`
- `sub_agent_result: str | None`
- `final_answer: str | None`

`RAGAgentState` and `AnalyticsAgentState` (internal, ephemeral):
- `messages: Annotated[list[BaseMessage], add_messages]`
- `business_key: str`

**Prompt files** — create all five `.txt` files:

`orchestrator_v1.txt` — Intent classifier. Instructions: output exactly one word from `["rag", "analytics", "general"]`. Rules: `rag` = documents/business knowledge; `analytics` = Instagram/Facebook metrics/posts/engagement; `general` = greetings/off-topic. Must include 5–6 few-shot examples inline and end with: "Respond with only one word."

`synthesizer_v1.txt` — Instructs orchestrator to rewrite the raw sub-agent response into a polished final answer: maintain assistant tone, preserve source citations, remove tool-calling artifacts (`Action:`, `Observation:` prefixes).

`rag_v1.txt` — RAG sub-agent: always call `search_documents` before answering, cite with `[n] Source:` notation, refuse to fabricate.

`analytics_v1.txt` — Analytics sub-agent: social media analytics specialist, always retrieve live data via tools, call `get_instagram_accounts_tool` first if no account_id is specified, explain metrics in plain language.

`direct_response_v1.txt` — Short conversational system prompt for greetings and general questions; guide user toward RAG or analytics questions.

**`src/agents/rag/__init__.py`** and **`src/agents/analytics/__init__.py`** — empty files.

---

### Step 2 — RAG Sub-Agent (`src/agents/rag/graph.py`)

- Module-level `_rag_agent = None` cache (no checkpointer)
- `_get_rag_llm()` — returns `ChatOpenAI` from `settings.rag_model/temperature/max_tokens`
- `_build_rag_agent()` — calls `build_rag_tool()` (existing, unchanged import from `tools.rag_tool`), loads `get_agent_prompt("rag")`, calls `create_react_agent(model, tools=[rag_tool], prompt=rag_prompt)` with no checkpointer
- `invoke_rag_agent(message: str, business_key: str) -> str` — public function; lazy-init; invokes with `{"messages": [{"role": "user", "content": message}], "business_key": business_key}`; returns `result["messages"][-1].content`

---

### Step 3 — Analytics Tools (`src/agents/analytics/tools.py`)

**The async-in-sync problem**: existing analytics functions (`get_accounts()`, etc.) are all `async def`. LangChain `@tool` functions run synchronously inside the agent loop. But `asyncio.run()` inside an already-running FastAPI event loop raises `RuntimeError`. 

**Solution**: each tool spawns a fresh thread via a module-level `_TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=2)` and runs the coroutine there:
```python
result = _TOOL_EXECUTOR.submit(asyncio.run, the_async_coroutine(...)).result()
```
This thread has no running event loop, so `asyncio.run()` works cleanly. This matches the pattern already used in `main.py`.

**Tools to create** (each as a `@tool`-decorated function with detailed docstrings):
1. `get_instagram_accounts_tool()` — wraps `get_accounts()` from `mcp_server.instagram.analytics`; returns JSON string of accounts
2. `get_instagram_overview_metrics_tool(account_id, since, until, period)` — wraps `get_overview_metrics_by_account_id()`
3. `get_instagram_top_posts_tool(account_id, since, until, limit)` — wraps `get_top_posts_by_account_id()`
4. `get_instagram_engagement_breakdown_tool(account_id, since, until)` — wraps `get_engagement_breakdown_by_account_id()`
5. `get_instagram_audience_demographics_tool(account_id)` — wraps `get_audience_demographics_by_account_id()`
6. `get_facebook_pages_tool()` — wraps `get_pages()` from `mcp_server.facebook.analytics`
7. `get_facebook_reach_tool(page_name)` — wraps `get_reach()`

Date inputs: `since`/`until` accept ISO strings (`"YYYY-MM-DD"`); each tool parses with `datetime.fromisoformat(...).replace(tzinfo=timezone.utc)` before calling the analytics function. If not provided or empty, pass `None` to use the analytics function's default window.

Graceful fallback: if `settings.facebook_access_token` is `None`, all tools return `"No social media token configured."` instead of raising.

---

### Step 4 — Analytics Sub-Agent (`src/agents/analytics/graph.py`)

Mirrors the RAG graph structure:
- `_analytics_agent = None` cache
- `_get_analytics_llm()` — `settings.analytics_model/temperature/max_tokens`
- `_build_analytics_agent()` — imports all tools from `analytics.tools`, loads `get_agent_prompt("analytics")`, calls `create_react_agent(model, tools=[all_7_tools], prompt=analytics_prompt)` with no checkpointer
- `invoke_analytics_agent(message: str, business_key: str) -> str` — same lazy-init and invocation pattern

---

### Step 5 — Orchestrator Graph (`src/agents/graph.py` — full replacement)

Module-level setup (unchanged from today):
- `_CHECKPOINT_DB = settings.chroma_persist_dir.parent / "checkpoints.db"`
- `sqlite3.connect(...)` with `check_same_thread=False`
- `_checkpointer = SqliteSaver(_conn)`
- `_graph = None` singleton

**Node functions** (all take `OrchestratorState`, return `dict`):

`classify_intent(state)`:
- Calls orchestrator LLM (`gpt-4o`) with `orchestrator_v1.txt` prompt + last user message
- Returns `{"intent": <one of rag/analytics/general>}`

`call_rag_agent(state)`:
- Calls `invoke_rag_agent(state["messages"][-1].content, state["business_key"])`
- Returns `{"sub_agent_result": <string>}`

`call_analytics_agent(state)`:
- Calls `invoke_analytics_agent(state["messages"][-1].content, state["business_key"])`
- Returns `{"sub_agent_result": <string>}`

`synthesize(state)`:
- Calls orchestrator LLM with `synthesizer_v1.txt` prompt, passing user query + `sub_agent_result`
- Returns `{"final_answer": <text>, "messages": [AIMessage(content=<text>)]}`

`direct_response(state)`:
- Calls orchestrator LLM with `direct_response_v1.txt` prompt
- Returns `{"final_answer": <text>, "messages": [AIMessage(content=<text>)]}`

**Routing function** `route_intent(state) -> str`:
- Reads `state["intent"]`, returns node name string

**Graph wiring**:
```
StateGraph(OrchestratorState)
  entry: classify_intent
  conditional_edges(classify_intent, route_intent, {
      "rag": call_rag_agent,
      "analytics": call_analytics_agent,
      "general": direct_response
  })
  edge: call_rag_agent → synthesize → END
  edge: call_analytics_agent → synthesize → END
  edge: direct_response → END
```

**`get_agent()`** — compiles with `graph.compile(checkpointer=_checkpointer)`, caches in `_graph`.
**`build_agent(business_key="")`** — compatibility shim, returns `get_agent()`.

---

### Step 6 — `src/api/main.py` (minimal change)

Only the `chat` handler changes:

```python
# Before:
agent.invoke(
    {"messages": [{"role": "user", "content": req.message}]},
    config={"configurable": {"thread_id": req.thread_id}},
)
answer = result["messages"][-1].content

# After:
agent.invoke(
    {
        "messages": [{"role": "user", "content": req.message}],
        "business_key": req.business_key,
    },
    config={"configurable": {"thread_id": req.thread_id}},
)
answer = result.get("final_answer") or result["messages"][-1].content
```

No other changes to `main.py`.

---

## Files Modified vs Created

| File | Action |
|------|--------|
| `src/agents/graph.py` | Full replacement |
| `src/agents/prompts.py` | Add `get_agent_prompt()` |
| `src/agents/state.py` | New |
| `src/agents/rag/__init__.py` | New (empty) |
| `src/agents/rag/graph.py` | New |
| `src/agents/analytics/__init__.py` | New (empty) |
| `src/agents/analytics/graph.py` | New |
| `src/agents/analytics/tools.py` | New |
| `config/config.yaml` | Add `agents:` block |
| `src/config/settings.py` | Add per-agent model settings |
| `src/api/main.py` | 2-line change in `chat` handler |
| `config/prompts/orchestrator_v1.txt` | New |
| `config/prompts/synthesizer_v1.txt` | New |
| `config/prompts/rag_v1.txt` | New |
| `config/prompts/analytics_v1.txt` | New |
| `config/prompts/direct_response_v1.txt` | New |

**Untouched**: `src/tools/rag_tool.py`, `src/mcp_server/`, `src/ingestion/`, all existing prompt files.

---

## Verification

1. **Settings load**: `python -c "from config.settings import settings; print(settings.rag_model)"` → prints `gpt-4o-mini`
2. **RAG agent standalone**: `invoke_rag_agent("What are the café opening hours?", "cafe")` returns a non-empty string with citations
3. **Analytics tool sync wrapper**: call `get_instagram_accounts_tool.invoke({})` from a plain Python script (not inside async loop) — must not raise `RuntimeError`
4. **Analytics agent standalone**: `invoke_analytics_agent("Show my top Instagram posts", "solar")` returns data or graceful no-token message
5. **Intent classification**: POST 10 sample messages, verify labels (`rag`/`analytics`/`general`) via server logs or debug state inspection
6. **Full chat flow**: POST `{"business_key": "cafe", "thread_id": "t1", "message": "What are the opening hours?"}` → response has `answer`, no tool artifacts
7. **Follow-up memory**: POST same `thread_id` with `"What about on Sundays?"` → answer uses prior context
8. **Analytics flow**: POST `{"message": "What were my top Instagram posts?", ...}` → routes to analytics, returns data or graceful fallback
9. **General flow**: POST `{"message": "Hello!", ...}` → routes `direct_response`, `final_answer` is a greeting
