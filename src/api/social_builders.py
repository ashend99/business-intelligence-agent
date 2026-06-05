"""Pure async payload builders for the social dashboard tabs.

No FastAPI dependencies — callable from route handlers, the background
poller, and tests alike.  Validation (HTTPException, Query params) lives
in main.py route handlers; these functions raise plain ValueError or
RuntimeError on bad input.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from api.social_overview import build_social_overview
from mcp_server.instagram.analytics import (
    get_engagement_breakdown_by_account_id,
    get_top_posts_by_account_id,
    get_posts_metrics_by_account_id,
)

logger = logging.getLogger(__name__)

_INSTAGRAM_MAX_LOOKBACK_DAYS = 90
_EMPTY_BREAKDOWN: dict[str, int] = {
    "likes": 0, "comments": 0, "saves": 0,
    "shares": 0, "reposts": 0, "replies": 0, "other": 0,
}


# ---------------------------------------------------------------------------
# Date helpers (no HTTPException — callers handle conversion)
# ---------------------------------------------------------------------------

def _parse_date(value: str | None, *, is_until: bool = False) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    if is_until:
        return parsed + timedelta(days=1)
    return parsed


# ---------------------------------------------------------------------------
# Engagement breakdown
# ---------------------------------------------------------------------------

def _empty_breakdown_payload(
    platform: str,
    account_id: str | None,
    link_to_window: bool,
) -> dict[str, Any]:
    return {
        "platform": platform,
        "account_id": account_id,
        "link_to_window": bool(link_to_window),
        "window_days": 30,
        "breakdown": dict(_EMPTY_BREAKDOWN),
        "previous_breakdown": dict(_EMPTY_BREAKDOWN),
        "total_interactions": 0,
        "previous_total_interactions": 0,
    }


async def build_engagement_breakdown(
    platform: str,
    account_id: str | None,
    since: str | None,
    until: str | None,
    link_to_window: bool,
) -> dict[str, Any]:
    """Return engagement breakdown for the given window.

    When link_to_window=False, uses the trailing 30-day window.
    Raises ValueError if account_id is missing for Instagram.
    """
    if platform != "ig":
        return _empty_breakdown_payload(platform, account_id, link_to_window)

    if not account_id:
        raise ValueError("account_id is required for Instagram engagement breakdown")

    default_since_date = None
    default_until_date = None

    if link_to_window:
        since_date = datetime.fromisoformat(since).date() if since else None
        until_date = datetime.fromisoformat(until).date() if until else None
        window_days = ((until_date - since_date).days + 1) if since_date and until_date else 30
        parsed_since = _parse_date(since)
        parsed_until = _parse_date(until, is_until=True)
    else:
        today = datetime.now(timezone.utc).date()
        default_since_date = today - timedelta(days=29)
        default_until_date = today
        parsed_since = datetime.combine(default_since_date, datetime.min.time(), tzinfo=timezone.utc)
        parsed_until = (
            datetime.combine(default_until_date, datetime.min.time(), tzinfo=timezone.utc)
            + timedelta(days=1)
        )
        window_days = 30

    prev_since = parsed_since - timedelta(days=int(window_days))
    prev_until = parsed_since
    prev_window_ok = (parsed_until - prev_since).days <= _INSTAGRAM_MAX_LOOKBACK_DAYS

    async def _empty_prev() -> dict:
        return {"breakdown": dict(_EMPTY_BREAKDOWN), "total_interactions": 0}

    current_payload, prev_payload = await asyncio.gather(
        get_engagement_breakdown_by_account_id(account_id, since=parsed_since, until=parsed_until),
        get_engagement_breakdown_by_account_id(account_id, since=prev_since, until=prev_until)
        if prev_window_ok else _empty_prev(),
        return_exceptions=True,
    )

    if isinstance(current_payload, Exception):
        raise current_payload

    prev_breakdown = (
        (prev_payload.get("breakdown") or _EMPTY_BREAKDOWN)
        if isinstance(prev_payload, dict)
        else dict(_EMPTY_BREAKDOWN)
    )
    prev_total = (
        (prev_payload.get("total_interactions") or 0)
        if isinstance(prev_payload, dict)
        else 0
    )

    return {
        "platform": platform,
        "account_id": account_id,
        "link_to_window": bool(link_to_window),
        "window_days": int(window_days),
        **current_payload,
        # Override since/until from the API response — it returns the +1 day query boundary, not the display date
        "since": since if link_to_window else (default_since_date.isoformat() if default_since_date else None),
        "until": until if link_to_window else (default_until_date.isoformat() if default_until_date else None),
        "previous_breakdown": prev_breakdown,
        "previous_total_interactions": int(prev_total),
    }


# ---------------------------------------------------------------------------
# Top posts
# ---------------------------------------------------------------------------

async def build_top_posts(
    platform: str,
    account_id: str | None,
    since: str | None,
    until: str | None,
    limit: int,
    link_to_window: bool,
) -> dict[str, Any]:
    """Return top posts for one account.

    Raises ValueError if account_id is missing for Instagram.
    """
    if platform != "ig":
        return {
            "platform": platform,
            "account_id": account_id,
            "link_to_window": bool(link_to_window),
            "posts": [],
        }

    if not account_id:
        raise ValueError("account_id is required for Instagram top posts")

    parsed_since = _parse_date(since) if link_to_window else None
    parsed_until = _parse_date(until, is_until=True) if link_to_window else None

    posts = await get_top_posts_by_account_id(
        account_id,
        since=parsed_since,
        until=parsed_until,
        limit=limit,
    )
    return {
        "platform": platform,
        "account_id": account_id,
        "link_to_window": bool(link_to_window),
        "since": since if link_to_window else None,
        "until": until if link_to_window else None,
        "posts": posts,
    }


# ---------------------------------------------------------------------------
# Posts metrics (lifetime)
# ---------------------------------------------------------------------------

async def build_posts_metrics(
    platform: str,
    account_id: str | None,
) -> dict[str, Any]:
    """Return lifetime posts metrics for one Instagram account."""
    if platform != "ig":
        return {
            "platform": platform,
            "account_id": account_id,
            "scope": "lifetime",
            "posts": [],
        }

    if not account_id:
        raise ValueError("account_id is required for posts metrics")

    posts = await get_posts_metrics_by_account_id(account_id)
    return {
        "platform": platform,
        "account_id": account_id,
        "scope": "lifetime",
        "posts": posts,
    }


# ---------------------------------------------------------------------------
# Analytics tab payload
# ---------------------------------------------------------------------------

async def build_analytics_payload(
    platform: str,
    account_id: str | None,
    since: str | None,
    until: str | None,
    period: str,
    timezone_name: str,
    top_posts_limit: int,
    compare_previous: bool,
    include_sections: list,
    include_kpis: list,
) -> dict[str, Any]:
    """Build the full /api/social/analytics response dict."""
    partial_errors: list[dict[str, str]] = []
    link_to_window = bool(since and until and compare_previous)

    # KPI cards — re-use overview builder for the selected window
    try:
        overview_payload = await build_social_overview(
            platform=platform,
            selected_account_id=account_id,
            since=since,
            until=until,
            period=period,
            timezone_name=timezone_name,
        )
    except Exception as exc:
        raise RuntimeError(f"overview fetch failed: {exc}") from exc

    overview_kpis = (
        overview_payload.get("kpis", {})
        if isinstance(overview_payload.get("kpis", {}), dict)
        else {}
    )
    cards = {
        "kpis_window": {
            key: value for key, value in overview_kpis.items()
            if (not include_kpis or key in include_kpis)
        }
    }

    sections: dict[str, Any] = {}

    if not include_sections or "engagement_breakdown_window" in include_sections:
        try:
            sections["engagement_breakdown_window"] = await build_engagement_breakdown(
                platform=platform,
                account_id=account_id,
                since=since,
                until=until,
                link_to_window=link_to_window,
            )
        except Exception as exc:
            partial_errors.append({"part": "engagement_breakdown_window", "message": str(exc)})

    if not include_sections or "top_performance_posts_window" in include_sections:
        try:
            sections["top_performance_posts_window"] = await build_top_posts(
                platform=platform,
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
        current_breakdown = (
            breakdown_payload.get("breakdown", {}) if isinstance(breakdown_payload, dict) else {}
        )
        previous_breakdown = (
            breakdown_payload.get("previous_breakdown", {}) if isinstance(breakdown_payload, dict) else {}
        )
        rows = []
        for metric_key in ["likes", "comments", "shares", "reposts", "replies", "saves"]:
            current_value = int(current_breakdown.get(metric_key, 0) or 0)
            previous_value = int(previous_breakdown.get(metric_key, 0) or 0)
            diff = current_value - previous_value
            diff_pct = (
                (diff / previous_value * 100.0) if previous_value > 0
                else (100.0 if current_value > 0 else 0.0)
            )
            rows.append({
                "metric": metric_key,
                "current": current_value,
                "previous": previous_value,
                "change": diff,
                "change_pct": round(diff_pct, 2),
            })
        sections["engagement_metric_details"] = {
            "since": breakdown_payload.get("since") if isinstance(breakdown_payload, dict) else since,
            "until": breakdown_payload.get("until") if isinstance(breakdown_payload, dict) else until,
            "rows": rows,
        }

    return {
        "tab": "analytics",
        "meta": {
            "platform": platform,
            "account_id": account_id,
            "since": since,
            "until": until,
            "timezone": timezone_name,
            "generated_at": f"{datetime.utcnow().isoformat()}Z",
        },
        "cards": cards,
        "sections": sections,
        "partial_errors": partial_errors,
    }


# ---------------------------------------------------------------------------
# Posts tab payload
# ---------------------------------------------------------------------------

async def build_posts_payload(
    platform: str,
    account_id: str | None,
    scope: str,
    since: str | None,
    until: str | None,
    sort_by: str,
    limit: int,
    page: int,
    include_sections: list,
    include_cards: list,
) -> dict[str, Any]:
    """Build the full /api/social/posts response dict."""
    partial_errors: list[dict[str, str]] = []
    raw_posts_payload: dict[str, Any] = {
        "platform": platform,
        "account_id": account_id,
        "scope": scope,
        "posts": [],
    }

    try:
        if scope == "lifetime":
            raw_posts_payload = await build_posts_metrics(platform=platform, account_id=account_id)
        else:
            raw_posts_payload = await build_top_posts(
                platform=platform,
                account_id=account_id,
                since=since,
                until=until,
                limit=limit,
                link_to_window=bool(since and until),
            )
    except Exception as exc:
        partial_errors.append({"part": "all_posts_table", "message": str(exc)})

    posts = (
        raw_posts_payload.get("posts", [])
        if isinstance(raw_posts_payload.get("posts", []), list)
        else []
    )

    sortable_fields = {
        "engagement_total": lambda row: float(row.get("engagement_total", 0) or 0),
        "reach": lambda row: float(row.get("reach", 0) or 0),
        "created_at": lambda row: row.get("created_at", "") or "",
    }
    sorter = sortable_fields.get(sort_by, sortable_fields["engagement_total"])
    sorted_posts = sorted(posts, key=sorter, reverse=True)

    start = (page - 1) * limit
    paged_posts = sorted_posts[start: start + limit]

    total_posts = len(posts)
    total_engagement = sum(float(row.get("engagement_total", 0) or 0) for row in posts)
    avg_engagement_rate = (
        sum(float(row.get("engagement_rate", 0) or 0) for row in posts) / total_posts
        if total_posts > 0 else 0.0
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

    sections: dict[str, Any] = {}
    if not include_sections or "all_posts_table" in include_sections:
        sections["all_posts_table"] = {"total": total_posts, "rows": paged_posts}
    if not include_sections or "posts_type_breakdown" in include_sections:
        sections["posts_type_breakdown"] = type_counts
    if not include_sections or "pagination" in include_sections:
        sections["pagination"] = {
            "page": page,
            "limit": limit,
            "total": total_posts,
            "has_next": (start + limit) < total_posts,
        }

    return {
        "tab": "posts",
        "meta": {
            "platform": platform,
            "account_id": account_id,
            "since": since,
            "until": until,
            "scope": scope,
            "generated_at": f"{datetime.utcnow().isoformat()}Z",
        },
        "cards": cards,
        "sections": sections,
        "partial_errors": partial_errors,
    }
