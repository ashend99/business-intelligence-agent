# Architecture v0.2
**Date:** 2026-05-12  
**Status:** Phase 2 complete — ingestion pipeline, RAG tool, and agent layer built and tested.

---

## Overview

A modular, local-first Agentic AI business intelligence chatbot that serves three businesses from a single agent. Retrieval is scoped per-business at the tool level; the LLM and memory layer are shared.

```
build_agent(business_key)          ← agent/graph.py
       │
       ├── ChatOpenAI (GPT-4o)
       ├── MemorySaver (session memory, keyed by thread_id)
       ├── system prompt (config/prompts/system_v1.txt)
       └── build_rag_tool(business_key) ─┐
                                         │
                              ┌──────────▼──────────┐
                              │  ChromaDB collection │
                              │  (one per business)  │
                              └─────────────────────┘
```

---

## Directory Structure

```
.
├── config/
│   ├── config.yaml                  # All non-secret config (model, paths, versions)
│   └── prompts/
│       └── system_v1.txt            # Active system prompt (versioned)
│
├── vectorstore/
│   └── chroma_db/                   # Persisted ChromaDB collections (populated by indexer)
│
├── src/
│   ├── config/
│   │   └── settings.py              # Central config singleton (reads config.yaml + .env)
│   │
│   ├── ingestion/
│   │   ├── loader.py                # Load PDF, DOCX, XLSX, CSV, TXT → List[Document]
│   │   ├── splitter.py              # Chunk documents (RecursiveCharacterTextSplitter)
│   │   └── indexer.py               # Embed + upsert chunks into ChromaDB
│   │
│   ├── tools/
│   │   └── rag_tool.py              # build_rag_tool(business_key) → LangChain @tool
│   │
│   ├── agent/
│   │   ├── prompts.py               # get_system_prompt() → loads versioned .txt file
│   │   └── graph.py                 # build_agent(business_key) → compiled LangGraph agent
│   │
│   └── tests/
│       ├── ingestion/               # Tests for loader, splitter, indexer
│       ├── tools/                   # 25 tests for rag_tool
│       └── agent/                   # 11 tests for prompts + graph
│
├── pyproject.toml                   # Dependencies managed with uv; src/ layout
└── .env                             # OPENAI_API_KEY (not committed)
```

---

## Component Details

### Config (`config/config.yaml` + `src/config/settings.py`)

Single source of truth for all non-secret values. `settings` is a singleton imported wherever config is needed.

| Key | Value |
|-----|-------|
| `llm.model` | `gpt-4o` |
| `embeddings.model` | `text-embedding-3-small` |
| `vectorstore.persist_dir` | `./vectorstore/chroma_db` |
| `collections.cafe` | `cafe_restaurant` |
| `collections.hotel` | `airport_hotel` |
| `collections.gems` | `gem_business` |
| `retrieval.top_k` | `5` |
| `ingestion.chunk_size` | `1000` |
| `ingestion.chunk_overlap` | `150` |
| `agent.prompt_version` | `v1` |
| `agent.prompts_dir` | `./config/prompts` |

---

### Ingestion Pipeline (`src/ingestion/`)

Run once (or on new documents) to populate ChromaDB.

```
source file
     │
     ▼
loader.py       load_document(path) → List[Document]
     │
     ▼
splitter.py     split_documents(docs) → List[Document]  (chunks)
     │
     ▼
indexer.py      index_documents(chunks, business_key)
                  → upserts into ChromaDB collection
```

- Deduplication: chunks are upserted by deterministic ID (`<source>_chunk_<n>`), so re-running is safe.
- Supported formats: `.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`

---

### RAG Tool (`src/tools/rag_tool.py`)

Two-stage retrieval: vector search → cross-encoder rerank.

```
query
  │
  ▼
ChromaDB.query(n_results = top_k × 3)    # over-fetch
  │
  ▼
FlashRank reranker (ms-marco-MiniLM-L-12-v2)
  │
  ▼
top_k results → formatted numbered list
  [1] Source: file.txt
  <chunk content>
  ---
  [2] ...
```

`build_rag_tool("cafe")` returns a LangChain `@tool` named `search_documents` bound to the `cafe_restaurant` collection. The agent calls it automatically via the ReAct loop.

---

### Agent Layer (`src/agent/`)

#### Prompt versioning (`prompts.py`)

Prompts live in `config/prompts/` as plain text files. The active version is controlled by `config.yaml`:

```yaml
agent:
  prompt_version: "v1"
  prompts_dir: "./config/prompts"
```

To introduce a new version: copy `system_v1.txt` → `system_v2.txt`, edit it, set `prompt_version: "v2"`. No code changes needed.

#### Agent graph (`graph.py`)

```python
agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o"),
    tools=[build_rag_tool(business_key)],
    prompt=get_system_prompt(),
    checkpointer=MemorySaver(),
)
```

Invocation:

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": question}]},
    config={"configurable": {"thread_id": session_id}},
)
answer = result["messages"][-1].content
```

- **Session memory**: `MemorySaver` maintains full conversation history per `thread_id`. Memory is in-process only.
- **Business scoping**: one RAG tool per agent instance, bound to one ChromaDB collection.

---

## Testing

| Module | Tests | Status |
|--------|-------|--------|
| `ingestion/loader.py` | 35 | ✅ passing |
| `ingestion/splitter.py` | covered | ✅ passing |
| `ingestion/indexer.py` | covered | ✅ passing |
| `tools/rag_tool.py` | 25 | ✅ passing |
| `agent/prompts.py` | 5 | ✅ passing |
| `agent/graph.py` | 6 | ✅ passing |

```
python -m pytest src/tests/ -v
```

---

## Key Technology Choices

| Concern | Choice | Reason |
|---------|--------|--------|
| LLM | GPT-4o | Strong reasoning and native tool/function calling |
| Embeddings | `text-embedding-3-small` | Fast, cost-effective, high quality |
| Vector store | ChromaDB (local, persistent) | No infrastructure needed |
| Reranker | FlashRank (ms-marco-MiniLM-L-12-v2) | Local, no API key, lightweight |
| Agent framework | LangGraph `create_react_agent` | Built-in checkpointing and tool loop |
| Session memory | `MemorySaver` | Zero config, in-process |
| Package manager | `uv` | Fast resolver; `pyproject.toml` as single source of truth |

