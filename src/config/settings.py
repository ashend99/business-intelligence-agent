"""
Module: src/config/settings.py
Date: 2026-05-07

Loads all application configuration from two sources:
  - .env file        → secrets (OPENAI_API_KEY)
  - config.yaml      → non-secret configuration (models, paths, etc.)

Usage:
    from config.settings import settings

    print(settings.openai_api_key)
    print(settings.llm_model)
    print(settings.chunk_size)
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve project root (two levels up from this file: src/config/settings.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.getenv("AGENT_HOME") or \
                                Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = Path(PROJECT_ROOT) / "config" / "config.yaml"
ENV_FILE = Path(PROJECT_ROOT) / ".env"

# Load .env — does nothing if file is missing (safe for production envs
# where variables are injected directly)
load_dotenv(ENV_FILE)


def _load_yaml(path: Path) -> dict:
    """Read and parse a YAML file, returning an empty dict on failure."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings:
    """
    Central configuration object for the application.

    Attributes are populated from config.yaml, with secrets sourced
    from environment variables (set via .env locally).
    """

    def __init__(self) -> None:
        cfg = _load_yaml(CONFIG_FILE)

        # --- Secrets (from environment) ---
        self.openai_api_key: str = self._get_env("OPENAI_API_KEY")

        # --- App ---
        app = cfg.get("app", {})
        self.app_title: str = app.get("title", "Business Intelligence Agent")
        self.log_level: str = app.get("log_level", "INFO")

        # --- LLM ---
        llm = cfg.get("llm", {})
        self.llm_model: str = llm.get("model", "gpt-4o")
        self.llm_temperature: float = llm.get("temperature", 0.0)
        self.llm_max_tokens: int = llm.get("max_tokens", 2048)

        # --- Embeddings ---
        embeddings = cfg.get("embeddings", {})
        self.embedding_model: str = embeddings.get("model", "text-embedding-3-small")

        # --- Vector store ---
        vs = cfg.get("vectorstore", {})
        self.vectorstore_provider: str = vs.get("provider", "chroma")
        self.chroma_persist_dir: Path = Path(PROJECT_ROOT) / vs.get(
            "persist_dir", "./vectorstore/chroma_db"
        ).lstrip("./")
        self.collections: dict[str, str] = vs.get(
            "collections",
            {"cafe": "cafe_restaurant", "hotel": "airport_hotel", "gems": "gem_business"},
        )

        # --- Ingestion ---
        ing = cfg.get("ingestion", {})
        self.docs_dir: Path = Path(PROJECT_ROOT) / ing.get("docs_dir", "./docs").lstrip("./")
        self.chunk_size: int = ing.get("chunk_size", 1000)
        self.chunk_overlap: int = ing.get("chunk_overlap", 150)
        self.supported_extensions: list[str] = ing.get(
            "supported_extensions", [".pdf", ".docx", ".xlsx", ".csv", ".txt"]
        )

        # --- Retrieval ---
        retrieval = cfg.get("retrieval", {})
        self.top_k: int = retrieval.get("top_k", 5)

        # --- Agent ---
        agent = cfg.get("agent", {})
        self.prompt_version: str = agent.get("prompt_version", "v1")
        self.prompts_dir: Path = Path(PROJECT_ROOT) / agent.get(
            "prompts_dir", "./config/prompts"
        ).lstrip("./")

    @staticmethod
    def _get_env(key: str) -> str:
        """Read a required environment variable, raising clearly if missing."""
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(
                f"Missing required environment variable: {key}\n"
                f"Add it to your .env file: {key}=<your-value>"
            )
        return value


# Single shared instance — import this everywhere
settings = Settings()
