# Component Architecture Diagram
**Date:** 2026-05-12

---

## High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION LAYER                                │
│                                                                             │
│   config/config.yaml  ──►  src/config/settings.py  ◄──  .env              │
│   config/prompts/                (singleton)              (secrets)         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ imported by all layers
          ┌────────────────────────┼─────────────────────────┐
          │                        │                         │
          ▼                        ▼                         ▼
┌─────────────────┐   ┌────────────────────────┐   ┌────────────────────┐
│  INGESTION      │   │  AGENT LAYER           │   │  UI LAYER          │
│  LAYER          │   │                        │   │                    │
│                 │   │  agent/prompts.py      │   │  ui/app.py         │
│  ingestion/     │   │  └─ get_system_prompt()│   │  ui/pages/         │
│  ├─ loader.py   │   │     reads versioned    │   │  ├─ 1_Chat.py      │
│  ├─ splitter.py │   │     .txt from disk     │   │  └─ 2_Documents.py │
│  └─ indexer.py  │   │                        │   │                    │
│                 │   │  agent/graph.py         │   └────────┬───────────┘
└────────┬────────┘   │  └─ build_agent(key)   │            │
         │            │     create_react_agent  │            │ calls
         │ upsert     │     + MemorySaver       │            ▼
         ▼            └────────────┬────────────┘   ┌────────────────────┐
┌─────────────────┐                │ uses           │  agent/graph.py    │
│  VECTOR STORE   │                ▼               │  build_agent(key)  │
│                 │   ┌────────────────────────┐   └────────────────────┘
│  ChromaDB       │   │  TOOLS LAYER           │
│  (persistent)   │◄──│                        │
│                 │   │  tools/rag_tool.py      │
│  Collections:   │   │  └─ build_rag_tool(key)│
│  cafe_restaurant│   │     1. query ChromaDB  │
│  airport_hotel  │   │        (over-fetch ×3) │
│  gem_business   │   │     2. FlashRank rerank│
│                 │   │     3. format results  │
└─────────────────┘   └────────────────────────┘
```

---

## Detailed Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  src/ui/app.py  (Streamlit entry point)                                              │
│                                                                                      │
│  ┌──────────────────┐    ┌──────────────────────────────────────────────────────┐   │
│  │  Sidebar         │    │  Landing Page                                        │   │
│  │  ─────────────   │    │  ─────────────────────────────────────────────────   │   │
│  │  Business        │    │  Welcome message + navigation hints                  │   │
│  │  selector        │    │                                                      │   │
│  │  (radio)         │    │  Writes to: st.session_state.business_key            │   │
│  │                  │    │  Resets:    agent, thread_id, messages on switch     │   │
│  └──────────────────┘    └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│  src/ui/pages/1_Chat.py              │  │  src/ui/pages/2_Documents.py             │
│                                      │  │                                          │
│  Reads: session_state.business_key   │  │  Reads: session_state.business_key       │
│                                      │  │                                          │
│  st.session_state:                   │  │  ┌──────────────────────────────────┐   │
│  ├─ agent    (cached per business)   │  │  │  Collection Status               │   │
│  ├─ thread_id (uuid4, per session)   │  │  │  chunk count + collection name   │   │
│  └─ messages  (chat history)         │  │  └──────────────────────────────────┘   │
│                                      │  │                                          │
│  ┌──────────────────────────────┐    │  │  ┌──────────────────────────────────┐   │
│  │  build_agent(business_key)   │    │  │  │  File Uploader                   │   │
│  │  └─► agent.invoke(           │    │  │  │  pdf/docx/xlsx/csv/txt           │   │
│  │        messages,             │    │  │  │  ↓                               │   │
│  │        thread_id config      │    │  │  │  load_document(tmp_path)         │   │
│  │      )                       │    │  │  │  ↓                               │   │
│  └──────────────────────────────┘    │  │  │  split_documents(docs)           │   │
│                                      │  │  │  ↓                               │   │
│  ┌──────────────────────────────┐    │  │  │  index_documents(chunks, key)    │   │
│  │  Chat UI                     │    │  │  └──────────────────────────────────┘   │
│  │  ├─ st.chat_message (history)│    │  │                                          │
│  │  ├─ st.chat_input            │    │  │  ┌──────────────────────────────────┐   │
│  │  └─ Clear conversation btn   │    │  │  │  Danger Zone                     │   │
│  └──────────────────────────────┘    │  │  │  clear_collection(business_key)  │   │
└──────────────────────────────────────┘  │  │  (confirm by typing business key)│   │
                                          │  └──────────────────────────────────┘   │
                                          └──────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│  src/agent/graph.py  ─  build_agent(business_key)                                   │
│                                                                                      │
│  ┌───────────────────┐  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │  ChatOpenAI       │  │  get_system_prompt()  │  │  MemorySaver                 │  │
│  │  model: gpt-4o    │  │  reads               │  │  keyed by thread_id          │  │
│  │  temp: 0.0        │  │  config/prompts/      │  │  (in-process session memory) │  │
│  │  max_tokens: 2048 │  │  system_v1.txt        │  │                              │  │
│  └─────────┬─────────┘  └──────────┬───────────┘  └──────────────┬───────────────┘  │
│            └──────────────────────►│◄────────────────────────────┘                  │
│                                    ▼                                                 │
│                       create_react_agent(llm, tools, prompt, checkpointer)          │
│                                    │                                                 │
│                                    ▼                                                 │
│                       ┌────────────────────────┐                                    │
│                       │  build_rag_tool(key)   │                                    │
│                       │  search_documents @tool│                                    │
│                       └────────────────────────┘                                    │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│  src/tools/rag_tool.py  ─  build_rag_tool(business_key)                             │
│                                                                                      │
│   query string                                                                       │
│       │                                                                              │
│       ▼                                                                              │
│   OpenAIEmbeddings.embed_query(query)                                                │
│       │                                                                              │
│       ▼                                                                              │
│   ChromaDB.query(n_results = top_k × RERANK_FETCH_MULTIPLIER=3)                     │
│       │                                                                              │
│       ▼  (if candidates > top_k)                                                     │
│   FlashRank reranker  (ms-marco-MiniLM-L-12-v2, local, no API key)                  │
│       │                                                                              │
│       ▼                                                                              │
│   _format_results() → numbered list with source citations                           │
│       [1] Source: file.txt                                                           │
│       <content>                                                                      │
│       ---                                                                            │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│  src/ingestion/  ─  Ingestion Pipeline                                              │
│                                                                                      │
│   source file (pdf / docx / xlsx / csv / txt)                                        │
│       │                                                                              │
│       ▼                                                                              │
│   loader.py ─ load_document(path) → List[Document]                                  │
│       │       (UnstructuredLoader per file type)                                     │
│       ▼                                                                              │
│   splitter.py ─ split_documents(docs) → List[Document]                              │
│       │         RecursiveCharacterTextSplitter                                       │
│       │         chunk_size=1000, chunk_overlap=150                                   │
│       │         adds chunk_id to each chunk metadata                                 │
│       ▼                                                                              │
│   indexer.py ─ index_documents(chunks, business_key) → int                          │
│       │        OpenAIEmbeddings.embed_documents(texts)                               │
│       │        ChromaDB.upsert(ids, embeddings, documents, metadatas)               │
│       │        (idempotent — same chunk_id → update, not duplicate)                  │
│       ▼                                                                              │
│   ChromaDB collection (persisted to ./vectorstore/chroma_db/)                       │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────┐
│  Configuration Layer                                                                 │
│                                                                                      │
│  config/config.yaml                   .env                                          │
│  ├─ app.title, log_level              └─ OPENAI_API_KEY                             │
│  ├─ llm.model / temperature / tokens                                                 │
│  ├─ embeddings.model                                                                 │
│  ├─ vectorstore.persist_dir                                                          │
│  ├─ vectorstore.collections                                                          │
│  │    cafe  → cafe_restaurant                                                        │
│  │    hotel → airport_hotel                                                          │
│  │    gems  → gem_business                                                           │
│  ├─ ingestion.chunk_size / chunk_overlap / supported_extensions                     │
│  ├─ retrieval.top_k                                                                  │
│  └─ agent.prompt_version / prompts_dir                                              │
│                         │                                                            │
│                         ▼                                                            │
│              src/config/settings.py  (Settings singleton)                           │
│              imported by: indexer, rag_tool, graph, prompts                         │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow — Chat Request (end-to-end)

```
User types question in 1_Chat.py
         │
         ▼
agent.invoke({"messages": [question]}, config={"thread_id": session_id})
         │
         ▼
LangGraph ReAct loop
         │
         ├──► GPT-4o decides to call search_documents(query)
         │              │
         │              ▼
         │         rag_tool: embed query → ChromaDB → rerank → format
         │              │
         │              ▼
         │         returns numbered context [1][2][3]
         │
         └──► GPT-4o synthesises answer with citations
         │
         ▼
MemorySaver stores [question + answer] under thread_id
         │
         ▼
answer displayed in st.chat_message("assistant")
```

---

## Data Flow — Document Indexing

```
Admin uploads file in 2_Documents.py
         │
         ▼
load_document(tmp_path) → List[Document]
         │
         ▼
split_documents(docs) → List[Document] (chunks with chunk_id)
         │
         ▼
index_documents(chunks, business_key)
         ├─ embed via OpenAI text-embedding-3-small
         └─ upsert into ChromaDB collection (idempotent)
```
