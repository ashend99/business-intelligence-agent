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
    collections: dict[str, str] = settings.collections
    if business_key not in collections:
        raise KeyError(
            f"Unknown business key '{business_key}'. "
            f"Valid keys: {list(collections.keys())}"
        )
    return collections[business_key]


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
        parts.append(f"[{i}] Source: {source}\n{text.strip()}")

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_rag_tool(business_key: str):
    """
    Build and return a LangChain tool bound to the given business collection.

    The returned tool queries ChromaDB for the top-k most relevant chunks
    matching the user's question and returns them as a formatted string.

    Args:
        business_key: One of 'cafe', 'hotel', 'gems'.

    Returns:
        A LangChain BaseTool that the agent can call.

    Raises:
        KeyError: If business_key is not in the configured collections.
    """
    # Validate key eagerly so failures surface at agent init, not at query time.
    collection_name = _resolve_collection_name(business_key)
    top_k: int = settings.top_k

    @tool
    def search_documents(query: str) -> str:
        """
        Search the business document knowledge base for information relevant
        to the query. Use this tool whenever the user asks a question about
        the business — sales, revenue, operations, products, policies, etc.

        Args:
            query: A natural language question or search phrase.

        Returns:
            Relevant document excerpts with source citations.
        """
        logger.info(
            "RAG query for collection '%s': %s", collection_name, query
        )

        try:
            client = _get_chroma_client()
            collection = client.get_collection(name=collection_name)
        except Exception as exc:
            # Collection may not exist if no documents have been indexed yet.
            logger.warning("Collection '%s' not found: %s", collection_name, exc)
            return (
                f"No documents have been indexed for this business yet. "
                f"Please upload and ingest documents first."
            )

        embedder = _get_embedder()
        query_vector = embedder.embed_query(query)

        # Stage 1: over-fetch from ChromaDB (wide recall)
        fetch_k = min(top_k * RERANK_FETCH_MULTIPLIER, collection.count())
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"],
        )

        documents: list[str] = results["documents"][0]
        metadatas: list[dict] = results["metadatas"][0]
        distances: list[float] = results["distances"][0]

        logger.info(
            "Vector search retrieved %d candidates (distances: %s)",
            len(documents),
            [round(d, 4) for d in distances],
        )

        # Stage 2: rerank to top_k (high precision)
        if len(documents) > top_k:
            documents, metadatas = _rerank(query, documents, metadatas, top_k)

        return _format_results(documents, metadatas)

    return search_documents
