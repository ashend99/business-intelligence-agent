"""
Module: tools/rag_tool.py
Date: 2026-05-12

LangChain tool that retrieves relevant document chunks from ChromaDB,
reranks them with FlashRank, and formats them as context for the LLM.

Retrieval is a two-stage pipeline:
  1. Vector search  — fast ANN search in ChromaDB (high recall, lower precision)
  2. Reranking      — cross-encoder scores each chunk against the query
                      (higher precision, keeps only the most relevant top_k)

Over-fetching (top_k × RERANK_FETCH_MULTIPLIER) at stage 1 ensures the
reranker has enough candidates to choose from.

Public API:
    build_rag_tool(business_key) -> BaseTool
        Returns a LangChain tool bound to the given business collection.
        Call this once per agent session after the business key is known.
"""

import logging

import chromadb
from flashrank import Ranker, RerankRequest
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings

from config.settings import settings

logger = logging.getLogger(__name__)

# How many candidates to fetch from ChromaDB before reranking.
# Fetching more gives the reranker a wider pool → better final precision.
RERANK_FETCH_MULTIPLIER = 3

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_chroma_client() -> chromadb.PersistentClient:
    persist_dir = settings.chroma_persist_dir
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def _get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def _resolve_collection_name(business_key: str) -> str:
    """Collection name equals the business key directly."""
    return business_key


def _rerank(
    query: str,
    documents: list[str],
    metadatas: list[dict],
    top_k: int,
) -> tuple[list[str], list[dict]]:
    """
    Rerank retrieved chunks using a FlashRank cross-encoder.

    Cross-encoders jointly encode the query and each passage together,
    producing a more accurate relevance score than cosine similarity alone.

    Args:
        query:     The user's original question.
        documents: Raw text of each retrieved chunk.
        metadatas: Corresponding metadata dicts (same order as documents).
        top_k:     How many results to keep after reranking.

    Returns:
        Tuple of (reranked_documents, reranked_metadatas) trimmed to top_k.
    """
    ranker = Ranker()  # uses ms-marco-MiniLM-L-12-v2 by default (local, ~120 MB)

    passages = [
        {"id": i, "text": text, "meta": meta}
        for i, (text, meta) in enumerate(zip(documents, metadatas))
    ]
    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)

    # results are sorted by score descending; take top_k
    top_results = results[:top_k]

    reranked_docs = [r["text"] for r in top_results]
    reranked_metas = [r["meta"] for r in top_results]

    logger.info(
        "Reranked %d → %d chunks (top score: %.4f)",
        len(documents),
        len(reranked_docs),
        top_results[0]["score"] if top_results else 0.0,
    )
    return reranked_docs, reranked_metas


def _format_results(documents: list[str], metadatas: list[dict]) -> str:
    """
    Format retrieved chunks into a readable context block for the LLM.

    Each chunk is prefixed with its source filename so the agent can
    cite where the information came from.
    """
    if not documents:
        return "No relevant documents found."

    parts: list[str] = []
    for i, (text, meta) in enumerate(zip(documents, metadatas), start=1):
        source = meta.get("source", "unknown source")
        collection = meta.get("collection", "")
        label = f"{collection}/{source}" if collection else source
        parts.append(f"[{i}] Source: {label}\n{text.strip()}")

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_rag_tool():
    """
    Build and return a LangChain tool that searches across ALL business
    collections in ChromaDB, merges results, and reranks globally.

    Returns:
        A LangChain BaseTool the agent can call.
    """
    top_k: int = settings.top_k

    @tool
    def search_documents(query: str) -> str:
        """
        Search the knowledge base across all business collections for information
        relevant to the query. Use this tool whenever the user asks a question
        about any business — sales, revenue, operations, products, policies, etc.

        Args:
            query: A natural language question or search phrase.

        Returns:
            Relevant document excerpts with source and collection citations.
        """
        client = _get_chroma_client()
        embedder = _get_embedder()
        query_vector = embedder.embed_query(query)

        # Collect existing collections
        try:
            collection_names = [c.name for c in client.list_collections()]
        except Exception as exc:
            logger.warning("Could not list collections: %s", exc)
            return "No documents have been indexed yet."

        if not collection_names:
            return "No documents have been indexed yet. Please upload documents first."

        all_documents: list[str] = []
        all_metadatas: list[dict] = []

        for col_name in collection_names:
            try:
                collection = client.get_collection(name=col_name)
                count = collection.count()
                if count == 0:
                    continue
                fetch_k = min(top_k * RERANK_FETCH_MULTIPLIER, count)
                results = collection.query(
                    query_embeddings=[query_vector],
                    n_results=fetch_k,
                    include=["documents", "metadatas", "distances"],
                )
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                # Tag each chunk with its collection
                for meta in metas:
                    meta["collection"] = col_name
                all_documents.extend(docs)
                all_metadatas.extend(metas)
                logger.info("Fetched %d candidates from '%s'", len(docs), col_name)
            except Exception as exc:
                logger.warning("Skipping collection '%s': %s", col_name, exc)

        if not all_documents:
            return "No relevant documents found across any collection."

        # Global rerank across all collections
        if len(all_documents) > top_k:
            all_documents, all_metadatas = _rerank(query, all_documents, all_metadatas, top_k)

        return _format_results(all_documents, all_metadatas)

    return search_documents
