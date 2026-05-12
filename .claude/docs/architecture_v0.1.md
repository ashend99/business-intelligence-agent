# Business Intelligence Agent — Architecture v0.1

**Status:** Phase 1 complete (Ingestion Pipeline)
**Date:** 2026-05-11
**Stack:** Python 3.11+ · LangChain/LangGraph · OpenAI GPT-4o · ChromaDB · Streamlit

---

## 1. Overview

A single-agent business intelligence chatbot that answers questions about three
business domains owned by the same operator:

| Business Key | Full Name | Collection |
|---|---|---|
| `cafe` | Café & Restaurant | `cafe_restaurant` |
| `hotel` | Airport Hotel | `airport_hotel` |
| `gems` | Gem Business | `gem_business` |

Users upload documents (PDFs, DOCX, XLSX, CSV, TXT) and ask natural language
questions. The agent retrieves relevant context from ChromaDB and generates
grounded answers using GPT-4o.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI  (app.py)                   │
│   Admin: upload docs, trigger ingestion, manage collections     │
│   Chat:  select business, ask questions, view answers           │
└────────────────────────┬────────────────────────────────────────┘
                         │
           ┌─────────────▼──────────────┐
           │     LangGraph Agent        │  ← Phase 2
           │   (src/agent/graph.py)     │
           │                            │
           │  ┌─────────────────────┐   │
           │  │  System Prompt      │   │
           │  │  (prompts.py)       │   │
           │  └─────────────────────┘   │
           │  ┌─────────────────────┐   │
           │  │  GPT-4o (OpenAI)    │   │
           │  └─────────────────────┘   │
           │  ┌─────────────────────┐   │
           │  │  RAG Tool           │   │
           │  │  (tools/rag_tool.py)│   │
           └──┴──────────┬──────────┴───┘
                         │
           ┌─────────────▼──────────────┐
           │       ChromaDB             │
           │  (vectorstore/chroma_db/)  │
           │  3 collections (per biz)   │
           └─────────────┬──────────────┘
                         │
           ┌─────────────▼──────────────┐
           │    Ingestion Pipeline      │  ← Phase 1 ✅
           │                            │
           │  loader.py  → splitter.py  │
           │       → indexer.py         │
           └────────────────────────────┘
```

---

## 3. Project Structure

```
d:\LUSTER\Agentic AI\
├── .claude/
│   └── docs/
│       └── architecture_v0.1.md        ← this file
├── .env                                 # secrets (OPENAI_API_KEY)
├── .env.example
├── .gitignore
├── config/
│   └── config.yaml                     # all non-secret config
├── docs/                               # business documents (user-managed)
│   ├── cafe/
│   ├── hotel/
│   └── gems/
├── pyproject.toml                      # uv project + all dependencies
├── sourceme.sh                         # Git Bash env activation helper
├── src/
│   ├── config/
│   │   └── settings.py                 # central Settings object
│   ├── ingestion/
│   │   ├── loader.py                   # file → Document list
│   │   ├── splitter.py                 # Document list → chunks
│   │   └── indexer.py                  # chunks → ChromaDB (embed + upsert)
│   ├── tools/                          # ← Phase 2
│   │   └── rag_tool.py
│   ├── agent/                          # ← Phase 2
│   │   ├── prompts.py
│   │   └── graph.py
│   └── tests/
│       ├── config/
│       │   ├── conftest.py
│       │   └── test_settings.py
│       └── ingestion/
│           ├── conftest.py
│           ├── test_loader.py
│           ├── test_splitter.py
│           └── test_indexer.py
├── vectorstore/
│   └── chroma_db/                      # persisted ChromaDB (gitignored)
└── app.py                              # Streamlit UI ← Phase 3
```

---

## 4. Configuration

All non-secret config lives in `config/config.yaml`. Secrets are in `.env`.
The `Settings` singleton (`src/config/settings.py`) is the single access point
for all config values throughout the codebase.

### Key config values (`config/config.yaml`)

| Key | Default | Purpose |
|---|---|---|
| `llm.model` | `gpt-4o` | LLM for agent responses |
| `llm.temperature` | `0.0` | Deterministic outputs |
| `embeddings.model` | `text-embedding-3-small` | OpenAI embedding model |
| `vectorstore.persist_dir` | `./vectorstore/chroma_db` | ChromaDB on-disk path |
| `ingestion.chunk_size` | `1000` | Max chars per chunk |
| `ingestion.chunk_overlap` | `150` | Overlap between chunks |
| `retrieval.top_k` | `5` | Chunks returned per query |

---

## 5. Phase 1 — Ingestion Pipeline (Complete ✅)

The ingestion pipeline converts raw business documents into searchable vector
embeddings stored in ChromaDB. It is a three-stage linear pipeline.

### Stage 1 — `loader.py` — File Loading

**Entry point:** `load_document(file_path)`, `load_directory(directory)`

Reads files from disk and returns a list of LangChain `Document` objects.
Each `Document` contains `page_content` (raw text) and `metadata` (at minimum
`source`: the file path).

| Extension | Loader Used |
|---|---|
| `.pdf` | `PyPDFLoader` |
| `.docx` | `Docx2txtLoader` |
| `.xlsx` | `UnstructuredExcelLoader` |
| `.csv` | `CSVLoader` |
| `.txt` | `TextLoader` |

Unsupported extensions are silently skipped by `load_directory`. Missing files
raise `FileNotFoundError`. Unsupported extensions on `load_document` raise
`ValueError`.

---

### Stage 2 — `splitter.py` — Text Splitting

**Entry point:** `split_documents(docs, chunk_size=1000, chunk_overlap=150)`

Splits large documents into smaller overlapping chunks using
`RecursiveCharacterTextSplitter`. Chunking is necessary because:
- LLMs have context limits
- Smaller chunks improve retrieval precision

**Behaviour:**
- Empty documents are silently skipped
- Each output chunk has `chunk_id` added to its metadata (0-indexed, globally
  sequential across all input documents)
- `chunk_size <= 0` or `chunk_overlap >= chunk_size` raises `ValueError`

---

### Stage 3 — `indexer.py` — Embedding & Storage

**Entry point:** `index_documents(docs, business_key)`, `clear_collection(business_key)`

Embeds each chunk using OpenAI `text-embedding-3-small` and upserts the
resulting vectors into the appropriate ChromaDB collection.

**Key design decisions:**
- **Upsert, not insert** — re-ingesting the same file updates chunks in-place,
  never creates duplicates
- **Stable chunk IDs** — SHA-256 of `source::position` (first 32 hex chars),
  deterministic across runs
- **Cosine similarity** — collections are created with `hnsw:space: cosine`,
  which is the correct metric for OpenAI embeddings
- **Per-business collections** — `cafe`, `hotel`, `gems` each get their own
  ChromaDB collection so queries are always scoped to one domain

---

## 6. Data Flow (End-to-End)

```
User uploads file
      │
      ▼
loader.py          load_document(path)
      │             → [Document(page_content, metadata)]
      ▼
splitter.py        split_documents(docs, chunk_size, chunk_overlap)
      │             → [Document(..., metadata={chunk_id: 0}), ...]
      ▼
indexer.py         index_documents(chunks, business_key)
      │             → embed via OpenAI text-embedding-3-small
      │             → upsert into ChromaDB collection
      ▼
ChromaDB           vectorstore/chroma_db/
                   collection: cafe_restaurant | airport_hotel | gem_business
```

---

## 7. Testing Strategy

- **Framework:** `pytest` with fixtures in `conftest.py` per module
- **File fixtures:** Real files generated in `tmp_path` (no mocked file I/O)
- **External API mocking:** OpenAI embedding calls are mocked with
  `unittest.mock` — no real network calls in tests
- **ChromaDB isolation:** Each test gets a `PersistentClient` in its own
  `tmp_path` subdirectory — no shared state between tests

| Test file | Tests | Covers |
|---|---|---|
| `test_settings.py` | 12 | `_load_yaml()`, `Settings._get_env()` |
| `test_loader.py` | 35 | `load_document()`, `load_directory()` |
| `test_splitter.py` | ~20 | `split_documents()` |
| `test_indexer.py` | ~25 | `_make_chunk_id()`, `_resolve_collection_name()`, `get_or_create_collection()`, `index_documents()`, `clear_collection()` |

---

## 8. Phase 2 — Agent Layer (Planned)

| File | Purpose |
|---|---|
| `src/tools/rag_tool.py` | LangChain tool: query ChromaDB, return top-k chunks |
| `src/agent/prompts.py` | System prompt templates, one per business domain |
| `src/agent/graph.py` | LangGraph `StateGraph`: user input → tool call → LLM → response |

The agent will follow a standard ReAct loop:
1. Receive user question + selected business
2. Call `rag_tool` to retrieve relevant context
3. Pass context + question to GPT-4o with the domain system prompt
4. Return grounded answer

---

## 9. Phase 3 — Streamlit UI (Planned)

`app.py` will expose two panels:

- **Admin panel:** Upload documents, select business, trigger ingestion,
  clear/re-index a collection
- **Chat panel:** Select business, ask questions, view streamed answers with
  source citations

---

## 10. Dependencies

| Package | Version | Role |
|---|---|---|
| `langchain` | >=0.3 | Document types, loaders, splitters |
| `langchain-openai` | latest | GPT-4o + embeddings |
| `langgraph` | >=0.3 | Agent state graph |
| `chromadb` | >=0.6 | Local vector store |
| `openai` | latest | OpenAI API client |
| `streamlit` | >=1.40 | Web UI |
| `python-dotenv` | latest | `.env` loading |
| `pyyaml` | >=6.0 | YAML config parsing |
| `pypdf` | latest | PDF loading |
| `docx2txt` | >=0.8 | DOCX loading |
| `unstructured[xlsx]` | latest | XLSX loading |
| `uv` | latest | Package manager (replaces pip) |
