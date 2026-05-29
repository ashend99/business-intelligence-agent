"""
Module: src/config/settings.py
Date: 2026-05-07

Loads all application configuration from multiple sources:
  - .env file        → secrets (OPENAI_API_KEY)
  - config.yaml      → non-secret configuration (models, paths, etc.)
    - src/mcp_server/*/config.yaml → platform social config (routing, metrics, overview)

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
PROJECT_ROOT = os.getenv("PROJECT_DIR") or \
                                Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = Path(PROJECT_ROOT) / "config" / "config.yaml"
BUSINESS_CONFIG_FILE = Path(PROJECT_ROOT) / "config" / "business_config.yaml"
FACEBOOK_mcp_server_CONFIG_FILE = Path(PROJECT_ROOT) / "src" / "mcp_server" / "facebook" / "config.yaml"
INSTAGRAM_mcp_server_CONFIG_FILE = Path(PROJECT_ROOT) / "src" / "mcp_server" / "instagram" / "config.yaml"
ENV_FILE = Path(PROJECT_ROOT) / ".env"

# Load .env — does nothing if file is missing (safe for production envs
# where variables are injected directly)
load_dotenv(ENV_FILE, override=True)


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
        # Optional — social features are disabled gracefully when not set
        self.facebook_access_token: str | None = os.getenv("FACEBOOK_ACCESS_TOKEN") or None

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

        # --- Social (platform configs live under src/mcp_server/*/config.yaml) ---
        fb_cfg = _load_yaml(FACEBOOK_mcp_server_CONFIG_FILE)
        ig_cfg = _load_yaml(INSTAGRAM_mcp_server_CONFIG_FILE)

        fb_overview = fb_cfg.get("social_overview", {}) if isinstance(fb_cfg.get("social_overview", {}), dict) else {}
        ig_overview = ig_cfg.get("social_overview", {}) if isinstance(ig_cfg.get("social_overview", {}), dict) else {}

        default_supported_periods = ["day", "week", "days_28", "month", "lifetime", "total_over_range"]
        self.social_supported_periods: list[str] = (
            fb_overview.get("supported_periods")
            or ig_overview.get("supported_periods")
            or default_supported_periods
        )

        merged_defaults = {
            **(ig_overview.get("defaults", {}) if isinstance(ig_overview.get("defaults", {}), dict) else {}),
            **(fb_overview.get("defaults", {}) if isinstance(fb_overview.get("defaults", {}), dict) else {}),
        }
        merged_behavior = {
            **(ig_overview.get("behavior", {}) if isinstance(ig_overview.get("behavior", {}), dict) else {}),
            **(fb_overview.get("behavior", {}) if isinstance(fb_overview.get("behavior", {}), dict) else {}),
        }

        ig_metrics = ig_overview.get("metrics", {}) if isinstance(ig_overview.get("metrics", {}), dict) else {}
        fb_metrics = fb_overview.get("metrics", {}) if isinstance(fb_overview.get("metrics", {}), dict) else {}

        self.social_overview: dict = {
            "route": fb_overview.get("route") or ig_overview.get("route") or "/api/social/overview",
            "defaults": merged_defaults,
            "behavior": merged_behavior,
            "platform_rules": {
                "fb": {
                    "include_sections": fb_overview.get("include_sections", []),
                    "include_kpis": fb_overview.get("include_kpis", []),
                },
                "ig": {
                    "include_sections": ig_overview.get("include_sections", []),
                    "include_kpis": ig_overview.get("include_kpis", []),
                },
            },
            "metrics": {
                "insights": fb_metrics.get("insights") or ig_metrics.get("insights") or [],
                "snapshot_profile": {
                    "fb": fb_metrics.get("snapshot_profile", []),
                    "ig": ig_metrics.get("snapshot_profile", []),
                },
                "breakdowns": {
                    "fb": fb_metrics.get("breakdowns", []),
                    "ig": ig_metrics.get("breakdowns", []),
                },
            },
        }

        fb_analytics = fb_cfg.get("social_analytics", {}) if isinstance(fb_cfg.get("social_analytics", {}), dict) else {}
        ig_analytics = ig_cfg.get("social_analytics", {}) if isinstance(ig_cfg.get("social_analytics", {}), dict) else {}

        self.social_analytics: dict = {
            "route": fb_analytics.get("route") or ig_analytics.get("route") or "/api/social/analytics",
            "defaults": {
                **(ig_analytics.get("defaults", {}) if isinstance(ig_analytics.get("defaults", {}), dict) else {}),
                **(fb_analytics.get("defaults", {}) if isinstance(fb_analytics.get("defaults", {}), dict) else {}),
            },
            "behavior": {
                **(ig_analytics.get("behavior", {}) if isinstance(ig_analytics.get("behavior", {}), dict) else {}),
                **(fb_analytics.get("behavior", {}) if isinstance(fb_analytics.get("behavior", {}), dict) else {}),
            },
            "platform_rules": {
                "fb": {
                    "include_sections": fb_analytics.get("include_sections", []),
                    "include_kpis": fb_analytics.get("include_kpis", []),
                },
                "ig": {
                    "include_sections": ig_analytics.get("include_sections", []),
                    "include_kpis": ig_analytics.get("include_kpis", []),
                },
            },
            "metrics": {
                "insights": (
                    (fb_analytics.get("metrics", {}) if isinstance(fb_analytics.get("metrics", {}), dict) else {}).get("insights")
                    or (ig_analytics.get("metrics", {}) if isinstance(ig_analytics.get("metrics", {}), dict) else {}).get("insights")
                    or []
                ),
            },
        }

        fb_posts = fb_cfg.get("social_posts", {}) if isinstance(fb_cfg.get("social_posts", {}), dict) else {}
        ig_posts = ig_cfg.get("social_posts", {}) if isinstance(ig_cfg.get("social_posts", {}), dict) else {}

        self.social_posts: dict = {
            "route": fb_posts.get("route") or ig_posts.get("route") or "/api/social/posts",
            "defaults": {
                **(ig_posts.get("defaults", {}) if isinstance(ig_posts.get("defaults", {}), dict) else {}),
                **(fb_posts.get("defaults", {}) if isinstance(fb_posts.get("defaults", {}), dict) else {}),
            },
            "behavior": {
                **(ig_posts.get("behavior", {}) if isinstance(ig_posts.get("behavior", {}), dict) else {}),
                **(fb_posts.get("behavior", {}) if isinstance(fb_posts.get("behavior", {}), dict) else {}),
            },
            "platform_rules": {
                "fb": {
                    "include_sections": fb_posts.get("include_sections", []),
                    "include_cards": fb_posts.get("include_cards", []),
                },
                "ig": {
                    "include_sections": ig_posts.get("include_sections", []),
                    "include_cards": ig_posts.get("include_cards", []),
                },
            },
        }

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
