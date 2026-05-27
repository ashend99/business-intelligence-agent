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
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make src/ importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.indexer import clear_collection, delete_document, drop_collection, get_collection_count, list_all_collections, list_documents, rename_collection  # noqa: E402
from ingestion.upload_docs import DocumentUploadPipeline  # noqa: E402
from ingestion.vectordb import get_vector_db  # noqa: E402
from mcp.facebook.client import init_client as init_facebook_client, close_client as close_facebook_client  # noqa: E402
from mcp.facebook.analytics import get_pages, get_pages_field, get_reach  # noqa: E402
from mcp.instagram.client import init_client as init_instagram_client, close_client as close_instagram_client  # noqa: E402
from mcp.instagram.analytics import get_accounts, get_top_posts_by_account_id, get_all_posts_by_account_id, get_posts_metrics_by_account_id, get_engagement_breakdown_by_account_id, get_overview_metrics_by_account_id, get_audience_demographics_by_account_id  # noqa: E402
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
async def disable_social_http_cache(request: Request, call_next):
    """Disable HTTP caching for social endpoints during validation."""
    response = await call_next(request)
    if request.url.path.startswith("/api/social/"):
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
_SUPPORTED_SOCIAL_PERIODS = {
    "day",
    "week",
    "days_28",
    "month",
    "lifetime",
    "total_over_range",
}

_INSTAGRAM_MAX_LOOKBACK_DAYS = 90


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


@app.get("/api/social/overview")
async def social_overview(
    platform: str = Query(..., min_length=2, max_length=2),
    account_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    period: str = Query(default="day"),
    timezone: str = Query(default="UTC"),
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
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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
        return {"pages": [{"id": p.id, "name": p.name} for p in pages]}
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
    from agent.graph import get_agent  # local import to avoid hard dependency for non-chat endpoints

    _validate_key(req.business_key)

    agent = get_agent()
    loop = asyncio.get_event_loop()

    try:
        result = await loop.run_in_executor(
            _executor,
            lambda: agent.invoke(
                {"messages": [{"role": "user", "content": req.message}]},
                config={"configurable": {"thread_id": req.thread_id}},
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    answer: str = result["messages"][-1].content
    return {"answer": answer}


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