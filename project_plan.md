# Agentic AI — Business Intelligence Chatbot

## Project Overview

A modular, agentic AI chatbot for a multi-business owner (cafe & restaurant, airport hotel, gem business) to retrieve and query information across various data sources through a single conversational interface.

Built as a **learning project** — each phase introduces new AI concepts progressively.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Agent Framework | LangGraph (LangChain) |
| LLM | OpenAI GPT-4o |
| Vector Store | ChromaDB (local) → Pinecone/Weaviate (cloud later) |
| Embeddings | OpenAI text-embedding-3-small |
| UI | Streamlit |
| Deployment | Local → Cloud (future) |

---

## Architecture

```
Admin (Streamlit UI)
       │
       ▼
  [ Chat Interface ]  ←──────────────────────────────────────┐
       │                                                      │
       ▼                                                      │
  [ LangGraph Agent ]  ── decides which tool(s) to call      │
       │                                                      │
       ├──→ [ RAG Tool ]  → ChromaDB → returns doc chunks    │
       │         ↑                                            │
       │    [ Ingestion Pipeline ]                            │
       │    (UI upload OR folder watch)                       │
       │                                                      │
       ├──→ [ Future: Social Media Tool ]                     │
       ├──→ [ Future: Sales DB Tool ]                         │
       ├──→ [ Future: Website Analytics Tool ]                │
       └──→ [ Future: Sub-agents per business unit ]──────────┘
```

---

## Folder Structure

```
agentic-ai/
│
├── app.py                  # Streamlit entry point
│
├── agent/
│   ├── __init__.py
│   ├── graph.py            # LangGraph agent graph (nodes + edges)
│   └── prompts.py          # System prompts
│
├── tools/
│   ├── __init__.py
│   └── rag_tool.py         # RAG retrieval tool (first tool)
│   # future: social_media_tool.py, sales_tool.py, etc.
│
├── ingestion/
│   ├── __init__.py
│   ├── loader.py           # Load PDF, DOCX, XLSX, CSV, TXT
│   ├── splitter.py         # Chunk documents
│   └── indexer.py          # Embed + store in ChromaDB
│
├── memory/
│   ├── __init__.py
│   └── session_memory.py   # LangChain session chat history
│
├── vectorstore/
│   └── chroma_db/          # ChromaDB persisted data (gitignored)
│
├── docs/                   # Drop documents here for batch ingestion
│   ├── cafe/
│   ├── hotel/
│   └── gems/
│
├── config/
│   └── settings.py         # API keys, model names, paths (via .env)
│
├── .env                    # Secrets (gitignored)
├── .gitignore
└── requirements.txt
```

---

## Module Responsibilities & Learning Map

| Module | Responsibility | AI Concepts You Learn |
|---|---|---|
| `ingestion/` | Load, chunk, and index documents | Document loaders, chunking strategies, embeddings |
| `vectorstore/` | Store and retrieve vector embeddings | Vector databases, similarity search, cosine distance |
| `tools/` | Define callable tools for the agent | LangChain tool definition, function/tool calling |
| `agent/` | Orchestrate reasoning and tool use | LangGraph, agent loops, nodes, edges, planning |
| `memory/` | Maintain conversation context | Message history, buffer memory, session state |
| `app.py` | Admin-facing chat interface | Streamlit, session state, file uploads |

---

## Build Phases

### Phase 1 — Project Foundation
**Goal:** Set up the project skeleton, configuration, and document ingestion pipeline.

- [ ] Initialize project structure and virtual environment
- [ ] Set up `.env`, `config/settings.py`
- [ ] Build `ingestion/loader.py` — load PDF, DOCX, XLSX, CSV, TXT
- [ ] Build `ingestion/splitter.py` — chunk documents with overlap
- [ ] Build `ingestion/indexer.py` — embed chunks and store in ChromaDB
- [ ] Create `docs/` folder structure (cafe, hotel, gems)
- [ ] Write `requirements.txt`

**Concepts:** Document loaders, text splitters, embeddings, vector stores

---

### Phase 2 — RAG Tool + LangGraph Agent
**Goal:** Build the core agent that can answer questions from ingested documents.

- [ ] Build `tools/rag_tool.py` — similarity search against ChromaDB
- [ ] Build `agent/prompts.py` — system prompt with business context
- [ ] Build `agent/graph.py` — LangGraph agent with tool-calling loop
- [ ] Build `memory/session_memory.py` — in-session chat history
- [ ] Test agent in terminal (before adding UI)

**Concepts:** RAG, tool calling, LangGraph nodes/edges, ReAct pattern, memory buffers

---

### Phase 3 — Streamlit UI
**Goal:** Give the admin a clean web interface to chat and upload documents.

- [ ] Build `app.py` — chat interface with message history display
- [ ] Add file uploader (PDF, DOCX, XLSX, CSV) → triggers ingestion pipeline
- [ ] Add sidebar for business selector (cafe / hotel / gems)
- [ ] Session state management

**Concepts:** Streamlit session state, async-safe UI patterns

---

### Phase 4 — Batch Folder Ingestion
**Goal:** Allow documents to be dropped in `docs/` folders and auto-indexed.

- [ ] CLI script to scan and ingest all files in `docs/`
- [ ] Track already-indexed files (avoid re-indexing)
- [ ] Per-business namespace/collection in ChromaDB

**Concepts:** Persistent vector store management, metadata filtering

---

### Phase 5+ — Extended Data Sources (Future)
Planned tools to add as new modules:

| Tool | Data Source | Notes |
|---|---|---|
| Social Media Tool | Instagram, Facebook APIs | Metrics: reach, engagement, followers |
| Website Analytics Tool | Google Analytics API | Sessions, bounce rate, conversions |
| Mobile App Metrics Tool | Firebase / App store APIs | DAU, retention, ratings |
| Sales Tool | POS system / SQL DB | Revenue, top products, trends |
| Brand Documents Tool | Extended RAG | Marketing briefs, SOPs, brand guidelines |
| Multi-Agent Router | LangGraph supervisor | Route queries to business-specific sub-agents |

---

## Future Architecture (Multi-Agent)

```
[ Supervisor Agent ]
       │
       ├──→ [ Cafe & Restaurant Agent ]
       ├──→ [ Airport Hotel Agent ]
       └──→ [ Gem Business Agent ]
```

Each sub-agent will have its own tools, data sources, and system prompt tuned to that business context.

---

## Security Notes

- All API keys stored in `.env` — never committed to git
- `.gitignore` covers `.env`, `vectorstore/chroma_db/`, `__pycache__/`
- No user authentication needed in Phase 1-4 (single admin)
- Auth layer (JWT / OAuth) to be added when multi-user support is introduced

---

## Status

| Phase | Status |
|---|---|
| Phase 1 — Project Foundation | Not started |
| Phase 2 — RAG Tool + Agent | Not started |
| Phase 3 — Streamlit UI | Not started |
| Phase 4 — Batch Ingestion | Not started |
| Phase 5+ — Extended Sources | Planned |
