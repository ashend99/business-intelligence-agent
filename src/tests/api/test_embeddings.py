"""
tests/api/test_embeddings.py

Integration test — verifies the configured OpenAI embedding model is
reachable and the API key is valid.

Run only when you want to hit the real OpenAI API:
    pytest src/tests/api/test_embeddings.py -v -m integration
"""

import pytest
from langchain_openai import OpenAIEmbeddings

from config.settings import settings


pytestmark = pytest.mark.integration


def test_api_key_is_set():
    """API key must be present and non-placeholder."""
    key = settings.openai_api_key
    assert key, "OPENAI_API_KEY is not set"
    assert not key.startswith("your-"), "OPENAI_API_KEY looks like a placeholder"
    assert key.startswith("sk-"), "OPENAI_API_KEY does not start with 'sk-'"


def test_embedding_model_returns_vectors():
    """Embed a short string — confirms key is valid and model is reachable."""
    embedder = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    vectors = embedder.embed_documents(["test connectivity"])

    assert isinstance(vectors, list), "Expected a list of vectors"
    assert len(vectors) == 1, "Expected exactly one vector"
    assert len(vectors[0]) > 0, "Vector should not be empty"
    assert isinstance(vectors[0][0], float), "Vector elements should be floats"


def test_embedding_dimension_matches_model():
    """text-embedding-3-small produces 1536-dim vectors by default."""
    expected_dim = 1536
    embedder = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    vectors = embedder.embed_documents(["dimension check"])
    assert len(vectors[0]) == expected_dim, (
        f"Expected {expected_dim}-dim vector, got {len(vectors[0])}"
    )


def test_batch_embedding():
    """Multiple texts should each produce a vector."""
    texts = ["LUSTER Cafe revenue", "Hotel occupancy rate", "Jewelry sales Q2"]
    embedder = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    vectors = embedder.embed_documents(texts)

    assert len(vectors) == len(texts), "Should return one vector per input text"
    assert all(len(v) > 0 for v in vectors), "All vectors should be non-empty"
