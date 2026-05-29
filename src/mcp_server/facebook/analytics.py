"""Facebook analytics helpers backed by the Graph API."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from mcp_server.facebook.client import FacebookGraphClient, get_client

PROJECT_DIR = os.getenv("PROJECT_DIR") or Path(__file__).resolve().parents[3]
FACEBOOK_CONFIG_PATH = Path(PROJECT_DIR) / "src" / "mcp_server" / "facebook" / "config.yaml"
_PAGE_FIELDS = (
    "id,name,username,category,fan_count,followers_count,"
    "picture,cover,link,about,website,verification_status,"
    "is_published,access_token"
)
logger = logging.getLogger(__name__)


@dataclass
class FacebookPage:
    id: str
    name: str
    username: str = ""
    category: str = ""
    fan_count: int = 0
    followers_count: int = 0
    link: str = ""
    about: str = ""
    website: str = ""
    verification_status: str = ""
    is_published: bool = True
    picture_url: str = ""
    cover_url: str = ""
    access_token: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "FacebookPage":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            username=data.get("username", ""),
            category=data.get("category", ""),
            fan_count=data.get("fan_count", 0),
            followers_count=data.get("followers_count", 0),
            link=data.get("link", ""),
            about=data.get("about", ""),
            website=data.get("website", ""),
            verification_status=data.get("verification_status", "not_verified"),
            is_published=data.get("is_published", True),
            picture_url=(data.get("picture") or {}).get("data", {}).get("url", ""),
            cover_url=(data.get("cover") or {}).get("source", ""),
            access_token=data.get("access_token", ""),
            raw=data,
        )


async def get_pages(limit: int = 25) -> list[FacebookPage]:
    client = get_client()
    pages: list[FacebookPage] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {
            "fields": _PAGE_FIELDS,
            "limit": limit,
        }
        if cursor:
            params["after"] = cursor

        data = await client.get("/me/accounts", **params)

        for item in data.get("data", []):
            pages.append(FacebookPage.from_api(item))

        paging = data.get("paging", {})
        cursors = paging.get("cursors", {})
        next_cursor = cursors.get("after")
        has_next = bool(paging.get("next"))

        if has_next and next_cursor:
            cursor = next_cursor
        else:
            break

    return pages


async def get_pages_field(*fields: str, limit: int = 25) -> list[Any]:
    """
    Helper to fetch a specific field across all pages
    """
    if not fields:
        raise ValueError("Provide at least one field name.")
    pages = await get_pages(limit=limit)
    if len(fields) == 1:
        return [getattr(page, fields[0]) for page in pages]
    return [{f: getattr(page, f) for f in fields} for page in pages]


def _load_config() -> dict:
    with open(FACEBOOK_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize_value(value: object) -> int:
    if isinstance(value, dict):
        value = value.get("value", 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _pct_change(current: int, previous: int) -> str:
    if previous <= 0:
        return "0.0%"
    return f"{((current - previous) / previous) * 100:.1f}%"


def _format_compact(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _resolve_bounds(
    since: datetime | None,
    until: datetime | None,
    window_days: int,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_until = until or now
    resolved_since = since or (resolved_until - timedelta(days=window_days))
    if resolved_since >= resolved_until:
        raise ValueError("Invalid range: since must be earlier than until.")
    return resolved_since, resolved_until


def _build_reach_summary(
    payload: dict,
    metric_name: str,
    label: str,
) -> dict:
    series = []
    for metric in payload.get("data", []):
        if metric.get("name") != metric_name:
            continue
        for item in metric.get("values", []):
            series.append(
                {
                    "date": item.get("end_time"),
                    "value": _normalize_value(item.get("value", 0)),
                }
            )

    if not series:
        return {
            "label": label,
            "metric": metric_name,
            "value": "0",
            "total_count": 0,
            "delta": "0.0%",
            "spark": [],
            "current_total": 0,
            "previous_total": 0,
        }

    midpoint = max(len(series) // 2, 1)
    previous_points = series[:midpoint]
    current_points = series[midpoint:]
    if not current_points:
        current_points = previous_points
        previous_points = []

    current_total = sum(point["value"] for point in current_points)
    previous_total = sum(point["value"] for point in previous_points)
    total_count = sum(point["value"] for point in series)

    return {
        "label": label,
        "metric": metric_name,
        "value": _format_compact(total_count),
        "total_count": total_count,
        "delta": _pct_change(current_total, previous_total),
        "spark": [point["value"] for point in series],
        "current_total": current_total,
        "previous_total": previous_total,
    }

async def get_page_by_name(name: str) -> FacebookPage | None:
    pages = await get_pages()
    return next((page for page in pages if page.name == name), None)


async def get_page_by_id(page_id: str) -> FacebookPage | None:
    pages = await get_pages()
    return next((page for page in pages if page.id == page_id), None)


async def get_reach_for_page(
    page: FacebookPage,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
) -> dict:
    """Return summarized reach analytics for a specific page entity."""
    config = _load_config()
    route_template = config.get("routing", {}).get("insights_path")
    metric_cfg = config.get("metrics", {}).get("reach", {})
    metric_name = metric_cfg.get("name", "page_impressions_unique")
    resolved_period = period or metric_cfg.get("period", "day")
    window_days = int(metric_cfg.get("window_days", 28))

    if not route_template:
        raise ValueError("Missing routing.insights_path in src/facebook/config.yaml")
    if window_days < 1:
        raise ValueError("metrics.reach.window_days must be at least 1")
    if not page.access_token:
        raise ValueError(f"No page access token available for page: {page.name}")

    resolved_since, resolved_until = _resolve_bounds(since, until, window_days)
    insights_path = route_template.format(page_id=page.id)

    async with FacebookGraphClient(page.access_token) as client:
        request_started_at = datetime.now(timezone.utc).timestamp()
        payload = await client.get(
            insights_path,
            metric=metric_name,
            period=resolved_period,
            since=int(resolved_since.timestamp()),
            until=int(resolved_until.timestamp()),
        )
    logger.debug(
        "facebook_insights_fetch duration_ms=%s page_id=%s metric=%s period=%s since=%s until=%s",
        int((datetime.now(timezone.utc).timestamp() - request_started_at) * 1000),
        page.id,
        metric_name,
        resolved_period,
        resolved_since.date().isoformat(),
        resolved_until.date().isoformat(),
    )

    summary = _build_reach_summary(payload, metric_name, page.name)
    summary["page_name"] = page.name
    summary["page_id"] = page.id
    summary["period"] = resolved_period
    summary["since"] = resolved_since.date().isoformat()
    summary["until"] = resolved_until.date().isoformat()
    return summary


async def get_reach_by_page_id(
    page_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
) -> dict:
    page = await get_page_by_id(page_id)
    if page is None:
        raise ValueError(f"Facebook page not found: {page_id}")
    return await get_reach_for_page(page, since=since, until=until, period=period)


async def get_posts_count_for_page(page: FacebookPage) -> dict[str, Any]:
    """Return published post count for a Facebook page."""
    if not page.access_token:
        raise ValueError(f"No page access token available for page: {page.name}")

    async with FacebookGraphClient(page.access_token) as client:
        payload = await client.get(
            f"/{page.id}/published_posts",
            fields="id",
            limit=1,
            summary="true",
        )

    total_count = int(((payload.get("summary") or {}).get("total_count")) or 0)
    return {
        "label": "Posts",
        "metric": "posts_count",
        "value": _format_compact(total_count),
        "total_count": total_count,
        "current_total": total_count,
        "previous_total": 0,
        "delta": "0.0%",
        "spark": [],
    }


async def get_posts_count_by_page_id(page_id: str) -> dict[str, Any]:
    page = await get_page_by_id(page_id)
    if page is None:
        raise ValueError(f"Facebook page not found: {page_id}")
    return await get_posts_count_for_page(page)

async def get_reach(page_name: str) -> dict:
    """Return summarized reach analytics for a managed Facebook page."""
    page = await get_page_by_name(page_name)
    if page is None:
        raise ValueError(f"Facebook page not found: {page_name}")
    return await get_reach_for_page(page)
