"""FastAPI backend for the SOLAR BI Dashboard.

Exposes:
    POST   /api/chat
    GET    /api/documents/count/{business_key}
    POST   /api/documents/upload/{business_key}
    DELETE /api/documents/delete/{business_key}/{doc_name}
    DELETE /api/documents/delete/{business_key}          (body: {"doc_names": [...]})
    DELETE /api/documents/clear/{business_key}

Run with:
    uvicorn src.api.main:app --reload --port 8000
Or from the project root (with venv active):
    python -m uvicorn src.api.main:app --reload --port 8000
"""
import os
import re
import asyncio
import sys
import tempfile
import logging
import json
import queue
import threading
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Prevent OpenBLAS startup failures on constrained environments (especially with --reload).
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.indexer import clear_collection, delete_document, drop_collection, get_collection_count, list_all_collections, list_documents, rename_collection  # noqa: E402
from ingestion.upload_docs import DocumentUploadPipeline  # noqa: E402
from ingestion.vectordb import get_vector_db  # noqa: E402
from mcp_server.facebook.client import init_client as init_facebook_client, close_client as close_facebook_client  # noqa: E402
from mcp_server.facebook.analytics import get_pages, get_pages_field, get_reach  # noqa: E402
from mcp_server.instagram.client import init_client as init_instagram_client, close_client as close_instagram_client  # noqa: E402
from mcp_server.instagram.analytics import get_accounts, get_top_posts_by_account_id, get_all_posts_by_account_id, get_posts_metrics_by_account_id, get_engagement_breakdown_by_account_id, get_overview_metrics_by_account_id, get_audience_demographics_by_account_id  # noqa: E402
from api.social_overview import build_social_overview  # noqa: E402
from config.settings import settings  # noqa: E402

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)

# PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = os.getenv("PROJECT_DIR") or Path(__file__).resolve().parent.parent.parent
_BUSINESS_CONFIG_PATH = Path(PROJECT_DIR) / "config" / "business_config.yaml"


def _load_business_keys() -> list[str]:
    with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [b["key"] for b in cfg["business"]["businesses"]]


def _request_runtime_context() -> dict[str, str]:
    """Return a stable timestamp/timezone pair for a single request."""
    now = datetime.now().astimezone()
    return {
        "current_datetime": now.isoformat(),
        "current_timezone": now.tzname() or "local",
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources at startup and clean up on shutdown."""
    # Vector DB collections
    db = get_vector_db()
    for key in _load_business_keys():
        db.ensure_collection(key)
    # Graph API singleton — token comes from settings (loaded from .env)
    if settings.facebook_access_token:
        init_facebook_client(settings.facebook_access_token)
        init_instagram_client(settings.facebook_access_token)
    yield
    await close_facebook_client()
    await close_instagram_client()


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="SOLAR BI API", version="1.0.0", redirect_slashes=True, lifespan=lifespan)


@app.middleware("http")
async def disable_api_http_cache(request: Request, call_next):
    """Disable HTTP caching for API responses during validation."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def _load_valid_keys() -> set[str]:
    with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as _f:
        _cfg = yaml.safe_load(_f)
    return {b["key"] for b in _cfg["business"]["businesses"]}

VALID_KEYS = _load_valid_keys()


_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')
_OVERVIEW_CFG = settings.social_overview if isinstance(settings.social_overview, dict) else {}
_OVERVIEW_DEFAULTS = _OVERVIEW_CFG.get("defaults", {}) if isinstance(_OVERVIEW_CFG.get("defaults", {}), dict) else {}
_SOCIAL_OVERVIEW_ROUTE = str(_OVERVIEW_CFG.get("route", "/api/social/overview"))
_DEFAULT_SOCIAL_PERIOD = str(_OVERVIEW_DEFAULTS.get("period", "day"))
_DEFAULT_SOCIAL_TIMEZONE = str(_OVERVIEW_DEFAULTS.get("timezone", "UTC"))
_SUPPORTED_SOCIAL_PERIODS = set(settings.social_supported_periods or [
    "day",
    "week",
    "days_28",
    "month",
    "lifetime",
    "total_over_range",
])

_INSTAGRAM_MAX_LOOKBACK_DAYS = 90

_ANALYTICS_CFG = settings.social_analytics if isinstance(settings.social_analytics, dict) else {}
_ANALYTICS_DEFAULTS = _ANALYTICS_CFG.get("defaults", {}) if isinstance(_ANALYTICS_CFG.get("defaults", {}), dict) else {}
_ANALYTICS_BEHAVIOR = _ANALYTICS_CFG.get("behavior", {}) if isinstance(_ANALYTICS_CFG.get("behavior", {}), dict) else {}
_ANALYTICS_PLATFORM_RULES = _ANALYTICS_CFG.get("platform_rules", {}) if isinstance(_ANALYTICS_CFG.get("platform_rules", {}), dict) else {}
_SOCIAL_ANALYTICS_ROUTE = str(_ANALYTICS_CFG.get("route", "/api/social/analytics"))
_DEFAULT_ANALYTICS_PERIOD = str(_ANALYTICS_DEFAULTS.get("period", _DEFAULT_SOCIAL_PERIOD))
_DEFAULT_ANALYTICS_TIMEZONE = str(_ANALYTICS_DEFAULTS.get("timezone", _DEFAULT_SOCIAL_TIMEZONE))
_DEFAULT_ANALYTICS_TOP_POSTS_LIMIT = int(_ANALYTICS_DEFAULTS.get("top_posts_limit", 10) or 10)
_ANALYTICS_COMPARE_PREVIOUS_DEFAULT = bool(_ANALYTICS_BEHAVIOR.get("comparison_window", True))

_POSTS_CFG = settings.social_posts if isinstance(settings.social_posts, dict) else {}
_POSTS_DEFAULTS = _POSTS_CFG.get("defaults", {}) if isinstance(_POSTS_CFG.get("defaults", {}), dict) else {}
_POSTS_PLATFORM_RULES = _POSTS_CFG.get("platform_rules", {}) if isinstance(_POSTS_CFG.get("platform_rules", {}), dict) else {}
_SOCIAL_POSTS_ROUTE = str(_POSTS_CFG.get("route", "/api/social/posts"))
_DEFAULT_POSTS_PERIOD = str(_POSTS_DEFAULTS.get("period", _DEFAULT_SOCIAL_PERIOD))
_DEFAULT_POSTS_TIMEZONE = str(_POSTS_DEFAULTS.get("timezone", _DEFAULT_SOCIAL_TIMEZONE))
_DEFAULT_POSTS_SCOPE = str(_POSTS_DEFAULTS.get("scope", "lifetime"))
_DEFAULT_POSTS_SORT_BY = str(_POSTS_DEFAULTS.get("sort_by", "engagement_total"))
_DEFAULT_POSTS_LIMIT = int(_POSTS_DEFAULTS.get("limit", 50) or 50)


def _platform_rule(rules: dict, platform: str, key: str, default):
    platform_cfg = rules.get(platform, {}) if isinstance(rules.get(platform, {}), dict) else {}
    return platform_cfg.get(key, default)


def _validate_key(business_key: str) -> None:
    if business_key not in VALID_KEYS and not _SLUG_RE.match(business_key):
        raise HTTPException(status_code=400, detail=f"Invalid business_key: {business_key!r}. Must be a known key or a lowercase slug.")


def _validate_instagram_window(since: str | None, until: str | None) -> None:
    if not since or not until:
        return
    try:
        since_date = datetime.fromisoformat(since).date()
        until_date = datetime.fromisoformat(until).date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format for since/until. Use YYYY-MM-DD.") from exc

    if since_date > until_date:
        raise HTTPException(status_code=400, detail="Invalid date range: since must be earlier than or equal to until.")

    lookback_days = (until_date - since_date).days + 1
    if lookback_days > _INSTAGRAM_MAX_LOOKBACK_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Instagram insights supports up to {_INSTAGRAM_MAX_LOOKBACK_DAYS} days per request.",
        )


def _parse_social_date_or_none(value: str | None, *, is_until: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format for since/until. Use YYYY-MM-DD.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    if is_until:
        return parsed + timedelta(days=1)
    return parsed


class ChatRequest(BaseModel):
    business_key: str
    thread_id: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get(_SOCIAL_OVERVIEW_ROUTE)
async def social_overview(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    period: str = Query(default=_DEFAULT_SOCIAL_PERIOD),
    timezone: str = Query(default=_DEFAULT_SOCIAL_TIMEZONE),
    refresh: bool = Query(default=False),
) -> dict:
    """Return one aggregated overview payload for a social platform."""
    normalized_platform = platform.lower()
    request_started_at = datetime.now().timestamp()

    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    if period not in _SUPPORTED_SOCIAL_PERIODS:
        allowed = ", ".join(sorted(_SUPPORTED_SOCIAL_PERIODS))
        raise HTTPException(status_code=400, detail=f"Unsupported period: {period}. Allowed: {allowed}")
    if normalized_platform == "ig":
        _validate_instagram_window(since, until)

    if not settings.facebook_access_token:
        return {
            "platform": normalized_platform,
            "summary": {
                "accounts": [],
                "selected_account": None,
            },
            "kpis": {
                "reach": None,
            },
            "meta": {
                "partial_errors": [],
                "generated_at": None,
            },
        }

    try:
        print(
            f"social_overview request start platform={normalized_platform} account_id={account_id} since={since} until={until} period={period} timezone={timezone} refresh={refresh}"
        )
        payload = await build_social_overview(
            platform=normalized_platform,
            selected_account_id=account_id,
            since=since,
            until=until,
            period=period,
            timezone_name=timezone,
            force_refresh=refresh,
        )
        print(
            f"social_overview request complete platform={normalized_platform} account_id={account_id} duration_ms={int((datetime.now().timestamp() - request_started_at) * 1000)}"
        )
        print(f"social_overview payload: {payload}")
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get(_SOCIAL_ANALYTICS_ROUTE)
async def social_analytics_tab(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    period: str = Query(default=_DEFAULT_ANALYTICS_PERIOD),
    timezone: str = Query(default=_DEFAULT_ANALYTICS_TIMEZONE),
    top_posts_limit: int = Query(default=_DEFAULT_ANALYTICS_TOP_POSTS_LIMIT, ge=1, le=50),
    compare_previous: bool = Query(default=_ANALYTICS_COMPARE_PREVIOUS_DEFAULT),
    refresh: bool = Query(default=False),
) -> dict:
    """Return one aggregated payload for the Analytics tab."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    if period not in _SUPPORTED_SOCIAL_PERIODS:
        allowed = ", ".join(sorted(_SUPPORTED_SOCIAL_PERIODS))
        raise HTTPException(status_code=400, detail=f"Unsupported period: {period}. Allowed: {allowed}")
    if normalized_platform == "ig" and since and until:
        _validate_instagram_window(since, until)

    include_sections = _platform_rule(_ANALYTICS_PLATFORM_RULES, normalized_platform, "include_sections", [])
    include_kpis = _platform_rule(_ANALYTICS_PLATFORM_RULES, normalized_platform, "include_kpis", [])

    if not settings.facebook_access_token:
        return {
            "tab": "analytics",
            "meta": {
                "platform": normalized_platform,
                "account_id": account_id,
                "since": since,
                "until": until,
                "timezone": timezone,
                "generated_at": None,
            },
            "cards": {},
            "sections": {},
            "partial_errors": [],
        }

    partial_errors: list[dict[str, str]] = []

    try:
        overview_payload = await build_social_overview(
            platform=normalized_platform,
            selected_account_id=account_id,
            since=since,
            until=until,
            period=period,
            timezone_name=timezone,
            force_refresh=refresh,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    overview_kpis = overview_payload.get("kpis", {}) if isinstance(overview_payload.get("kpis", {}), dict) else {}
    cards = {
        "kpis_window": {
            key: value for key, value in overview_kpis.items()
            if (not include_kpis or key in include_kpis)
        }
    }

    sections: dict = {}
    link_to_window = bool(since and until and compare_previous)

    if not include_sections or "engagement_breakdown_window" in include_sections:
        try:
            sections["engagement_breakdown_window"] = await social_engagement_breakdown(
                platform=normalized_platform,
                account_id=account_id,
                since=since,
                until=until,
                link_to_window=link_to_window,
            )
        except Exception as exc:
            partial_errors.append({"part": "engagement_breakdown_window", "message": str(exc)})

    if not include_sections or "top_performance_posts_window" in include_sections:
        try:
            sections["top_performance_posts_window"] = await social_top_posts(
                platform=normalized_platform,
                account_id=account_id,
                since=since,
                until=until,
                limit=top_posts_limit,
                link_to_window=link_to_window,
            )
        except Exception as exc:
            partial_errors.append({"part": "top_performance_posts_window", "message": str(exc)})

    if not include_sections or "engagement_metric_details" in include_sections:
        breakdown_payload = sections.get("engagement_breakdown_window", {})
        current_breakdown = breakdown_payload.get("breakdown", {}) if isinstance(breakdown_payload, dict) else {}
        previous_breakdown = breakdown_payload.get("previous_breakdown", {}) if isinstance(breakdown_payload, dict) else {}
        metric_keys = ["likes", "comments", "shares", "reposts", "replies", "saves"]
        rows = []
        for metric_key in metric_keys:
            current_value = int(current_breakdown.get(metric_key, 0) or 0)
            previous_value = int(previous_breakdown.get(metric_key, 0) or 0)
            diff = current_value - previous_value
            diff_pct = (diff / previous_value * 100.0) if previous_value > 0 else (100.0 if current_value > 0 else 0.0)
            rows.append(
                {
                    "metric": metric_key,
                    "current": current_value,
                    "previous": previous_value,
                    "change": diff,
                    "change_pct": round(diff_pct, 2),
                }
            )
        sections["engagement_metric_details"] = {
            "since": breakdown_payload.get("since") if isinstance(breakdown_payload, dict) else since,
            "until": breakdown_payload.get("until") if isinstance(breakdown_payload, dict) else until,
            "rows": rows,
        }

    return {
        "tab": "analytics",
        "meta": {
            "platform": normalized_platform,
            "account_id": account_id,
            "since": since,
            "until": until,
            "timezone": timezone,
            "generated_at": f"{datetime.utcnow().isoformat()}Z",
        },
        "cards": cards,
        "sections": sections,
        "partial_errors": partial_errors,
    }


@app.get(_SOCIAL_POSTS_ROUTE)
async def social_posts_tab(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    period: str = Query(default=_DEFAULT_POSTS_PERIOD),
    timezone: str = Query(default=_DEFAULT_POSTS_TIMEZONE),
    scope: str = Query(default=_DEFAULT_POSTS_SCOPE),
    sort_by: str = Query(default=_DEFAULT_POSTS_SORT_BY),
    limit: int = Query(default=_DEFAULT_POSTS_LIMIT, ge=1, le=200),
    page: int = Query(default=1, ge=1),
) -> dict:
    """Return one aggregated payload for the Posts tab."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    if period not in _SUPPORTED_SOCIAL_PERIODS:
        allowed = ", ".join(sorted(_SUPPORTED_SOCIAL_PERIODS))
        raise HTTPException(status_code=400, detail=f"Unsupported period: {period}. Allowed: {allowed}")
    if normalized_platform == "ig" and since and until:
        _validate_instagram_window(since, until)

    include_sections = _platform_rule(_POSTS_PLATFORM_RULES, normalized_platform, "include_sections", [])
    include_cards = _platform_rule(_POSTS_PLATFORM_RULES, normalized_platform, "include_cards", [])

    if not settings.facebook_access_token:
        return {
            "tab": "posts",
            "meta": {
                "platform": normalized_platform,
                "account_id": account_id,
                "since": since,
                "until": until,
                "timezone": timezone,
                "scope": scope,
                "generated_at": None,
            },
            "cards": {},
            "sections": {},
            "partial_errors": [],
        }

    if normalized_platform == "ig" and not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for posts tab.")

    partial_errors: list[dict[str, str]] = []
    posts_payload: dict = {
        "platform": normalized_platform,
        "account_id": account_id,
        "scope": scope,
        "posts": [],
    }

    try:
        if scope == "lifetime":
            posts_payload = await social_posts_metrics(platform=normalized_platform, account_id=account_id)
        else:
            posts_payload = await social_top_posts(
                platform=normalized_platform,
                account_id=account_id,
                since=since,
                until=until,
                limit=limit,
                link_to_window=bool(since and until),
            )
    except Exception as exc:
        partial_errors.append({"part": "all_posts_table", "message": str(exc)})

    posts = posts_payload.get("posts", []) if isinstance(posts_payload.get("posts", []), list) else []

    sortable_fields = {
        "engagement_total": lambda row: float(row.get("engagement_total", 0) or 0),
        "reach": lambda row: float(row.get("reach", 0) or 0),
        "created_at": lambda row: row.get("created_at", "") or "",
    }
    sorter = sortable_fields.get(sort_by, sortable_fields["engagement_total"])
    sorted_posts = sorted(posts, key=sorter, reverse=True)

    start = (page - 1) * limit
    end = start + limit
    paged_posts = sorted_posts[start:end]

    total_posts = len(posts)
    total_engagement = sum(float(row.get("engagement_total", 0) or 0) for row in posts)
    avg_engagement_rate = (
        sum(float(row.get("engagement_rate", 0) or 0) for row in posts) / total_posts
        if total_posts > 0
        else 0.0
    )

    cards_all = {
        "total_posts": total_posts,
        "total_engagement": int(total_engagement),
        "avg_engagement_rate": round(avg_engagement_rate, 4),
    }
    cards = {k: v for k, v in cards_all.items() if (not include_cards or k in include_cards)}

    type_counts: dict[str, int] = {}
    for row in posts:
        media_type = str(row.get("type", "other") or "other").strip().lower()
        type_counts[media_type] = type_counts.get(media_type, 0) + 1

    sections: dict = {}
    if not include_sections or "all_posts_table" in include_sections:
        sections["all_posts_table"] = {
            "total": total_posts,
            "rows": paged_posts,
        }
    if not include_sections or "posts_type_breakdown" in include_sections:
        sections["posts_type_breakdown"] = type_counts
    if not include_sections or "pagination" in include_sections:
        sections["pagination"] = {
            "page": page,
            "limit": limit,
            "total": total_posts,
            "has_next": end < total_posts,
        }

    return {
        "tab": "posts",
        "meta": {
            "platform": normalized_platform,
            "account_id": account_id,
            "since": since,
            "until": until,
            "timezone": timezone,
            "period": period,
            "scope": scope,
            "generated_at": f"{datetime.utcnow().isoformat()}Z",
        },
        "cards": cards,
        "sections": sections,
        "partial_errors": partial_errors,
    }


# ---------------------------------------------------------------------------
# Social — Facebook
# ---------------------------------------------------------------------------

@app.get("/api/social/facebook/pages")
async def facebook_pages(
    fields: list[str] = Query(default=[]),
) -> dict:
    """Return Facebook Pages the configured token can manage.

    Args:
        fields: Optional list of :class:`FacebookPage` attribute names to
                extract (e.g. ``?fields=name&fields=fan_count``).
                When omitted, returns ``[{"id": "...", "name": "..."}]``
                — enough for a dropdown menu.

    Returns:
        ``{"pages": [...]}`` — flat values for a single field, dicts for
        multiple fields, or ``id+name`` objects when no fields are given.
    """
    if not settings.facebook_access_token:
        return {"pages": []}
    try:
        if fields:
            data = await get_pages_field(*fields)
            return {"pages": data}
        pages = await get_pages()
        return {
            "pages": [
                {
                    "id": p.id,
                    "name": p.name,
                    "picture_url": p.picture_url,
                    "followers_count": getattr(p, "followers_count", 0),
                    "fan_count": getattr(p, "fan_count", 0),
                }
                for p in pages
            ]
        }
    except AttributeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.get("/api/social/facebook/reach")
async def facebook_reach(page_name: str = Query(..., min_length=1)) -> dict:
    """Return summarized reach analytics for the requested Facebook Page."""
    if not settings.facebook_access_token:
        return {
            "page_name": page_name,
            "metric": "page_impressions_unique",
            "value": "0",
            "delta": "0.0%",
            "spark": [],
            "current_total": 0,
            "previous_total": 0,
        }
    try:
        return await get_reach(page_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

# ---------------------------------------------------------------------------
# Social — Instagram
# ---------------------------------------------------------------------------

@app.get("/api/social/instagram/accounts")
async def instagram_accounts() -> dict:
    """Return Instagram business accounts available to the configured token."""
    if not settings.facebook_access_token:
        return {"accounts": []}
    try:
        accounts = await get_accounts()
        return {
            "accounts": [
                {
                    "id": account.id,
                    "name": account.name,
                    "username": account.username,
                    "picture_url": account.profile_picture_url,
                    "followers_count": account.followers_count,
                    "follows_count": account.follows_count,
                    "media_count": account.media_count,
                    "page_id": account.page_id,
                    "page_name": account.page_name,
                }
                for account in accounts
            ]
        }
    except AttributeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/social/top-posts")
async def social_top_posts(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    link_to_window: bool = Query(default=False),
) -> dict:
    """Return top posts for one account without rebuilding the full overview payload."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    if not settings.facebook_access_token:
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "posts": [],
        }

    if normalized_platform != "ig":
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "posts": [],
        }

    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for Instagram top posts.")

    if link_to_window:
        _validate_instagram_window(since, until)

    parsed_since = _parse_social_date_or_none(since) if link_to_window else None
    parsed_until = _parse_social_date_or_none(until, is_until=True) if link_to_window else None

    try:
        posts = await get_top_posts_by_account_id(
            account_id,
            since=parsed_since,
            until=parsed_until,
            limit=limit,
        )
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "since": since if link_to_window else None,
            "until": until if link_to_window else None,
            "posts": posts,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/social/get_all_posts")
async def social_get_all_posts(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
) -> dict:
    """Return all lifetime posts for one account (Instagram only)."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    if not settings.facebook_access_token:
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": [],
        }

    if normalized_platform != "ig":
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": [],
        }

    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for lifetime posts.")

    try:
        posts = await get_all_posts_by_account_id(account_id)
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": posts,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/social/posts-metrics")
async def social_posts_metrics(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
) -> dict:
    """Return lifetime posts metrics based on media-level count fields (Instagram only)."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    if not settings.facebook_access_token:
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": [],
        }

    if normalized_platform != "ig":
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": [],
        }

    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for posts metrics.")

    try:
        posts = await get_posts_metrics_by_account_id(account_id)
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": posts,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Error in social_posts_metrics: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/social/audience-demographics")
async def social_audience_demographics(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
) -> dict:
    """Return lifetime engaged audience demographics (age, country, gender, gender-by-age)."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    empty = {
        "platform": normalized_platform,
        "account_id": account_id,
        "scope": "lifetime",
        "age": {},
        "country": {},
        "gender": {},
        "age_gender": {},
    }

    if not settings.facebook_access_token:
        return empty

    if normalized_platform != "ig":
        return empty

    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for audience demographics.")

    try:
        data = await get_audience_demographics_by_account_id(account_id)
        return {
            "platform": normalized_platform,
            **data,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/social/insights")
async def social_insights(
    platform: str = Query(..., min_length=2, max_length=2),
    metric: str | None = Query(default=None),  # reach, views, engagement, engagement_rate, etc.
    metrics: str | None = Query(default=None),  # comma-separated metric names
    period: str = Query(default="day"),
    metric_type: str = Query(default="total_value"),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
) -> dict:
    """Return aggregated insights metric for a date range.
    
    Returns single metric as total_value (summed over period) or rate.
    """
    normalized_platform = platform.lower()
    allowed_metrics = {"reach", "views", "engagement", "engagement_rate"}

    if metrics:
        requested_metrics = [m.strip().lower() for m in metrics.split(",") if m.strip()]
    elif metric:
        requested_metrics = [metric.strip().lower()]
    else:
        requested_metrics = ["reach", "views", "engagement", "engagement_rate"]

    if not requested_metrics:
        raise HTTPException(status_code=400, detail="At least one metric is required.")

    invalid_metrics = [m for m in requested_metrics if m not in allowed_metrics]
    if invalid_metrics:
        raise HTTPException(status_code=400, detail=f"Unsupported metric(s): {', '.join(invalid_metrics)}")

    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    if not settings.facebook_access_token:
        if len(requested_metrics) == 1:
            single_metric = requested_metrics[0]
            return {
                "platform": normalized_platform,
                "account_id": account_id,
                "metric": single_metric,
                "period": period,
                "metric_type": metric_type,
                "since": since,
                "until": until,
                "value": None,
                "data": [],
            }
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "metrics": {
                m: {
                    "metric": m,
                    "value": None,
                    "data": [],
                }
                for m in requested_metrics
            },
            "period": period,
            "metric_type": metric_type,
            "since": since,
            "until": until,
        }
    
    if normalized_platform != "ig":
        if len(requested_metrics) == 1:
            single_metric = requested_metrics[0]
            return {
                "platform": normalized_platform,
                "account_id": account_id,
                "metric": single_metric,
                "period": period,
                "metric_type": metric_type,
                "since": since,
                "until": until,
                "value": None,
                "data": [],
            }
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "metrics": {
                m: {
                    "metric": m,
                    "value": None,
                    "data": [],
                }
                for m in requested_metrics
            },
            "period": period,
            "metric_type": metric_type,
            "since": since,
            "until": until,
        }
    
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for insights.")
    
    if not since or not until:
        raise HTTPException(status_code=400, detail="since and until are required for insights.")
    
    _validate_instagram_window(since, until)
    
    try:
        parsed_since = _parse_social_date_or_none(since)
        parsed_until = _parse_social_date_or_none(until, is_until=True)

        overview_metrics = await get_overview_metrics_by_account_id(
            account_id,
            since=parsed_since,
            until=parsed_until,
            period=period,
        )

        reach_total = int((overview_metrics.get("reach") or {}).get("total_count") or 0)
        views_total = int((overview_metrics.get("views") or {}).get("total_count") or 0)
        engagement_total = int((overview_metrics.get("total_interactions") or {}).get("total_count") or 0)
        engagement_rate = (float(engagement_total) / float(reach_total) * 100.0) if reach_total > 0 else 0.0

        computed_metrics = {
            "reach": {
                "metric": "reach",
                "value": reach_total,
                "data": (overview_metrics.get("reach") or {}).get("spark") or [],
            },
            "views": {
                "metric": "views",
                "value": views_total,
                "data": (overview_metrics.get("views") or {}).get("spark") or [],
            },
            "engagement": {
                "metric": "engagement",
                "value": engagement_total,
                "data": (overview_metrics.get("total_interactions") or {}).get("spark") or [],
            },
            "engagement_rate": {
                "metric": "engagement_rate",
                "value": round(engagement_rate, 4),
                "data": [],
            },
        }

        if len(requested_metrics) == 1:
            single_metric = requested_metrics[0]
            metric_payload = computed_metrics.get(single_metric, {"metric": single_metric, "value": 0, "data": []})
            return {
                "platform": normalized_platform,
                "account_id": account_id,
                "metric": single_metric,
                "period": period,
                "metric_type": metric_type,
                "since": since,
                "until": until,
                "value": metric_payload.get("value", 0),
                "data": metric_payload.get("data", []),
            }

        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "metrics": {
                m: computed_metrics.get(m, {"metric": m, "value": 0, "data": []})
                for m in requested_metrics
            },
            "period": period,
            "metric_type": metric_type,
            "since": since,
            "until": until,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/social/engagement-breakdown")
async def social_engagement_breakdown(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    link_to_window: bool = Query(default=False),
) -> dict:
    """Return engagement breakdown payload for one card without rebuilding overview."""
    normalized_platform = platform.lower()
    if normalized_platform not in {"fb", "ig"}:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    if not settings.facebook_access_token:
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "window_days": 30,
            "breakdown": {
                "likes": 0,
                "comments": 0,
                "saves": 0,
                "shares": 0,
                "reposts": 0,
                "replies": 0,
                "other": 0,
            },
            "total_interactions": 0,
        }

    if normalized_platform != "ig":
        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "window_days": 30,
            "breakdown": {
                "likes": 0,
                "comments": 0,
                "saves": 0,
                "shares": 0,
                "reposts": 0,
                "replies": 0,
                "other": 0,
            },
            "total_interactions": 0,
        }

    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required for Instagram engagement breakdown.")

    default_since = None
    default_until = None

    if link_to_window:
        _validate_instagram_window(since, until)
        since_date = datetime.fromisoformat(since).date() if since else None
        until_date = datetime.fromisoformat(until).date() if until else None
        window_days = ((until_date - since_date).days + 1) if since_date and until_date else 30
        parsed_since = _parse_social_date_or_none(since)
        parsed_until = _parse_social_date_or_none(until, is_until=True)
    else:
        today = datetime.now(timezone.utc).date()
        default_since = today - timedelta(days=29)
        default_until = today
        parsed_since = datetime.combine(default_since, datetime.min.time(), tzinfo=timezone.utc)
        parsed_until = datetime.combine(default_until, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
        window_days = 30

    # Compute previous window (equal length immediately before current)
    prev_since = parsed_since - timedelta(days=int(window_days))
    prev_until = parsed_since
    prev_window_ok = (parsed_until - prev_since).days <= _INSTAGRAM_MAX_LOOKBACK_DAYS

    _empty_breakdown = {"likes": 0, "comments": 0, "saves": 0, "shares": 0, "reposts": 0, "replies": 0, "other": 0}

    async def _empty_prev() -> dict:
        return {"breakdown": _empty_breakdown, "total_interactions": 0}

    try:
        current_payload, prev_payload = await asyncio.gather(
            get_engagement_breakdown_by_account_id(account_id, since=parsed_since, until=parsed_until),
            get_engagement_breakdown_by_account_id(account_id, since=prev_since, until=prev_until)
            if prev_window_ok else _empty_prev(),
            return_exceptions=True,
        )
        if isinstance(current_payload, Exception):
            raise current_payload
        prev_breakdown = (prev_payload.get("breakdown") or _empty_breakdown) if isinstance(prev_payload, dict) else _empty_breakdown
        prev_total = (prev_payload.get("total_interactions") or 0) if isinstance(prev_payload, dict) else 0

        return {
            "platform": normalized_platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "window_days": int(window_days),
            "since": since if link_to_window else default_since.isoformat(),
            "until": until if link_to_window else default_until.isoformat(),
            **current_payload,
            "previous_breakdown": prev_breakdown,
            "previous_total_interactions": int(prev_total),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc



@app.get("/api/config")
async def get_config() -> dict:
    """Return the business configuration from business_config.yaml."""
    try:
        with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    """Invoke the LangGraph agent and return the assistant reply."""
    from agents.graph import get_agent  # local import to avoid hard dependency for non-chat endpoints

    _validate_key(req.business_key)

    agent = get_agent()
    loop = asyncio.get_event_loop()

    try:
        runtime_context = _request_runtime_context()
        result = await loop.run_in_executor(
            _executor,
            lambda: agent.invoke(
                {
                    "messages": [{"role": "user", "content": req.message}],
                    "business_key": req.business_key,
                    **runtime_context,
                },
                config={"configurable": {"thread_id": req.thread_id}},
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    answer: str = result.get("final_answer") or result["messages"][-1].content
    response: dict = {"answer": answer}
    if settings.show_reasoning:
        response["reasoning"] = result.get("reasoning_steps") or []
    return response


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Stream reasoning steps and final answer as NDJSON events."""
    from agents.graph import get_agent  # local import to avoid hard dependency for non-chat endpoints

    _validate_key(req.business_key)
    agent = get_agent()

    def _run_agent_stream(out_q: queue.Queue):
        try:
            runtime_context = _request_runtime_context()
            for state in agent.stream(
                {
                    "messages": [{"role": "user", "content": req.message}],
                    "business_key": req.business_key,
                    **runtime_context,
                },
                config={"configurable": {"thread_id": req.thread_id}},
                stream_mode="values",
            ):
                out_q.put(("state", state))
            out_q.put(("done", None))
        except Exception as exc:
            out_q.put(("error", str(exc)))

    async def event_generator():
        out_q: queue.Queue = queue.Queue()
        thread = threading.Thread(target=_run_agent_stream, args=(out_q,), daemon=True)
        thread.start()

        last_reasoning_index = 0
        latest_state: dict = {}

        while True:
            kind, payload = await asyncio.get_event_loop().run_in_executor(_executor, out_q.get)

            if kind == "state":
                latest_state = payload or {}
                if settings.show_reasoning:
                    reasoning_steps = latest_state.get("reasoning_steps") or []
                    if len(reasoning_steps) > last_reasoning_index:
                        new_steps = reasoning_steps[last_reasoning_index:]
                        last_reasoning_index = len(reasoning_steps)
                        for step in new_steps:
                            yield json.dumps({"type": "reasoning", "step": step}, ensure_ascii=True) + "\n"
                continue

            if kind == "error":
                yield json.dumps({"type": "error", "error": payload}, ensure_ascii=True) + "\n"
                break

            if kind == "done":
                answer = latest_state.get("final_answer")
                if not answer and latest_state.get("messages"):
                    answer = latest_state["messages"][-1].content
                response = {"type": "final", "answer": answer or ""}
                if settings.show_reasoning:
                    response["reasoning"] = latest_state.get("reasoning_steps") or []
                yield json.dumps(response, ensure_ascii=True) + "\n"
                break

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@app.get("/api/collections")
async def get_collections() -> dict:
    """Return all collection names that exist in the vector DB."""
    try:
        return {"collections": list_all_collections()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/documents/list/{business_key}")
async def doc_list(business_key: str) -> dict:
    """Return per-file document names and chunk counts for a collection."""
    _validate_key(business_key)
    try:
        docs = list_documents(business_key)
        return {"business_key": business_key, "documents": docs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/documents/count/{business_key}")
async def doc_count(business_key: str) -> dict:
    """Return the number of indexed chunks for a business collection."""
    _validate_key(business_key)
    try:
        count = get_collection_count(business_key)
        return {"business_key": business_key, "count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/documents/upload/{business_key}")
async def upload_docs(
    business_key: str,
    files: list[UploadFile] = File(...),
) -> dict:
    """
    Upload one or more files and run the ingestion pipeline.

    Args:
        business_key: The business collection to index into.
        files: List of files to upload (multipart/form-data).
    Returns:
        Dict with counts of processed files, indexed chunks, and any errors.
    """
    _validate_key(business_key)

    tmp_paths: list[Path] = []
    try:
        for f in files:
            # suffix = Path(f.filename or "file").suffix
            original_name = Path(f.filename or "file").name
            tmp_dir = Path(tempfile.mkdtemp())
            tmp_path = tmp_dir / original_name
            tmp_path.write_bytes(await f.read())
            tmp_paths.append(tmp_path)

        loop = asyncio.get_event_loop()
        pipeline = DocumentUploadPipeline(business_key)
        result = await loop.run_in_executor(
            _executor,
            lambda: pipeline.run(tmp_paths),
        )

        return {
            "files_processed": result.files_processed,
            "chunks_indexed": result.chunks_indexed,
            "errors": result.errors,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)
            try:
                p.parent.rmdir()
            except OSError:
                pass


class DeleteRequest(BaseModel):
    doc_names: list[str]


@app.delete("/api/documents/delete/{business_key}")
async def delete_docs_batch(business_key: str, req: DeleteRequest) -> dict:
    """Delete all chunks for multiple documents from a collection."""
    _validate_key(business_key)
    try:
        total = 0
        for name in req.doc_names:
            total += delete_document(business_key, name)
        return {"ok": True, "business_key": business_key, "doc_names": req.doc_names, "chunks_deleted": total}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/documents/delete/{business_key}/{doc_name}")
async def delete_doc(business_key: str, doc_name: str) -> dict:
    """Delete all chunks for a specific document from a collection."""
    _validate_key(business_key)
    try:
        deleted = delete_document(business_key, doc_name)
        return {"ok": True, "business_key": business_key, "doc_name": doc_name, "chunks_deleted": deleted}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/documents/clear/{business_key}")
async def clear_docs(business_key: str) -> dict:
    """Wipe and recreate the vector collection for a business."""
    _validate_key(business_key)
    try:
        clear_collection(business_key)
        return {"ok": True, "business_key": business_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Collection management (dynamic/custom collections only)
# ---------------------------------------------------------------------------

class RenameRequest(BaseModel):
    new_key: str


@app.delete("/api/collections/{collection_key}")
async def delete_collection_endpoint(collection_key: str) -> dict:
    """Delete an entire custom collection. Refuses pre-configured keys."""
    _validate_key(collection_key)
    if collection_key in VALID_KEYS:
        raise HTTPException(status_code=400, detail=f"Cannot delete a pre-configured collection: {collection_key!r}")
    try:
        drop_collection(collection_key)
        return {"ok": True, "deleted": collection_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/collections/{collection_key}/rename")
async def rename_collection_endpoint(collection_key: str, req: RenameRequest) -> dict:
    """Rename a custom collection. Refuses pre-configured keys."""
    _validate_key(collection_key)
    if collection_key in VALID_KEYS:
        raise HTTPException(status_code=400, detail=f"Cannot rename a pre-configured collection: {collection_key!r}")
    new_key = req.new_key.strip().lower().replace(" ", "_")
    if not _SLUG_RE.match(new_key):
        raise HTTPException(status_code=400, detail=f"Invalid collection name: {new_key!r}. Must be lowercase slug.")
    if new_key == collection_key:
        return {"ok": True, "old_key": collection_key, "new_key": new_key}
    try:
        rename_collection(collection_key, new_key)
        return {"ok": True, "old_key": collection_key, "new_key": new_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")