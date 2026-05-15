"""
tests/config/conftest.py

Fixtures for config/settings.py tests.

Strategy:
  - Write a minimal valid config.yaml to a temp directory
  - Point PROJECT_DIR to that temp directory so Settings resolves paths correctly
  - Set OPENAI_API_KEY via monkeypatch so no real .env is needed
"""

import textwrap
from pathlib import Path

import pytest


VALID_YAML = textwrap.dedent("""\
    app:
      title: "Test Agent"
      log_level: "DEBUG"

    llm:
      model: "gpt-4o"
      temperature: 0.2
      max_tokens: 1024

    embeddings:
      model: "text-embedding-3-small"

    vectorstore:
      persist_dir: "./vectorstore/chroma_db"
      collections:
        cafe: "cafe_restaurant"
        hotel: "airport_hotel"
        gems: "gem_business"

    ingestion:
      docs_dir: "./docs"
      chunk_size: 500
      chunk_overlap: 50
      supported_extensions:
        - ".pdf"
        - ".txt"

    retrieval:
      top_k: 3
""")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """
    A temporary directory that mimics the project root.
    Contains a valid config/config.yaml.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(VALID_YAML, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def settings_env(monkeypatch: pytest.MonkeyPatch, project_root: Path):
    """
    Patch environment so Settings() can be instantiated without a real .env.
    Sets PROJECT_DIR and OPENAI_API_KEY, then yields the project_root path.
    """
    monkeypatch.setenv("PROJECT_DIR", str(project_root))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-1234")
    yield project_root
