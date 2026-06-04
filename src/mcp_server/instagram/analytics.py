"""Instagram analytics helpers backed by the Graph API."""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mcp_server.instagram.client import get_client

PROJECT_DIR = os.getenv("PROJECT_DIR") or Path(__file__).resolve().parents[3]
INSTAGRAM_CONFIG_PATH = Path(PROJECT_DIR) / "src" / "mcp_server" / "instagram" / "config.yaml"
logger = logging.getLogger(__name__)


@dataclass
class InstagramAccount:
    """Instagram business account linked to a Facebook Page."""

    id: str
    name: str
    username: str = ""
    profile_picture_url: str = ""
    followers_count: int = 0
    follows_count: int = 0
    media_count: int = 0
    page_id: str = ""
    page_name: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, page_data: dict) -> "InstagramAccount | None":
        ig_data = page_data.get("instagram_business_account") or {}
        ig_id = ig_data.get("id")
        if not ig_id:
            return None

        return cls(
            id=ig_id,
            name=ig_data.get("username") or page_data.get("name", ""),
            username=ig_data.get("username", ""),
            profile_picture_url=ig_data.get("profile_picture_url", ""),
            followers_count=int(ig_data.get("followers_count") or 0),
            follows_count=int(ig_data.get("follows_count") or 0),
            media_count=int(ig_data.get("media_count") or 0),
            page_id=page_data.get("id", ""),
            page_name=page_data.get("name", ""),
            raw=page_data,
        )


def _load_config() -> dict:
    with open(INSTAGRAM_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        # Graph responses sometimes wrap numeric values in nested objects.
        for key in ("value", "total_value", "count", "total"):
            if key in value:
                return _normalize_value(value[key])
        for nested in value.values():
            normalized = _normalize_value(nested)
            if normalized != 0:
                return normalized
        return 0
    if isinstance(value, list):
        for item in value:
            normalized = _normalize_value(item)
            if normalized != 0:
                return normalized
        return 0
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


def _non_negative_int(value: int) -> int:
    return max(int(value or 0), 0)


def _build_metric_summary(
    payload: dict,
    metric_name: str,
    account: InstagramAccount,
    resolved_since: datetime,
    resolved_until: datetime,
    resolved_period: str,
) -> dict:
    series = []
    metric_title = ""
    metric_description = ""
    total_value: int | None = None

    for metric in payload.get("data", []):
        if metric.get("name") != metric_name:
            continue
        metric_title = metric.get("title") or metric_title
        metric_description = metric.get("description") or metric_description
        total_value_payload = metric.get("total_value") or {}
        if "value" in total_value_payload:
            total_value = _normalize_value(total_value_payload.get("value"))
        for item in metric.get("values", []):
            series.append(
                {
                    "date": item.get("end_time"),
                    "value": _normalize_value(item.get("value", 0)),
                }
            )
    if total_value is not None and not series:
        return {
            "account_id": account.id,
            "account_name": account.name,
            "metric": metric_name,
            "title": metric_title,
            "description": metric_description,
            "value": _format_compact(total_value),
            "total_count": total_value,
            "delta": "0.0%",
            "spark": [],
            "current_total": total_value,
            "previous_total": 0,
            "period": resolved_period,
            "since": resolved_since.date().isoformat(),
            "until": resolved_until.date().isoformat(),
        }

    if not series:
        return {
            "account_id": account.id,
            "account_name": account.name,
            "metric": metric_name,
            "title": metric_title,
            "description": metric_description,
            "value": "0",
            "total_count": 0,
            "delta": "0.0%",
            "spark": [],
            "current_total": 0,
            "previous_total": 0,
            "period": resolved_period,
            "since": resolved_since.date().isoformat(),
            "until": resolved_until.date().isoformat(),
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
        "account_id": account.id,
        "account_name": account.name,
        "metric": metric_name,
        "title": metric_title,
        "description": metric_description,
        "value": _format_compact(total_count),
        "total_count": total_count,
        "delta": _pct_change(current_total, previous_total),
        "spark": [point["value"] for point in series],
        "current_total": current_total,
        "previous_total": previous_total,
        "period": resolved_period,
        "since": resolved_since.date().isoformat(),
        "until": resolved_until.date().isoformat(),
    }


def _resolve_period_for_metrics(
    metric_names: tuple[str, ...],
    requested_period: str | None,
    config: dict,
) -> str:
    """Return the period to use, auto-correcting if it violates any metric's constraints.

    Computes the intersection of valid_periods across all requested metrics.
    If the requested period is not in that intersection (or no period was given),
    falls back to the first metric's configured default period.
    """
    metrics_cfg = config.get("metrics", {})
    default_period = metrics_cfg.get(metric_names[0], {}).get("period", "day") if metric_names else "day"

    valid_sets: list[set[str]] = []
    for name in metric_names:
        valid = metrics_cfg.get(name, {}).get("valid_periods")
        if valid:
            valid_sets.append(set(valid))

    intersection: set[str] = valid_sets[0].intersection(*valid_sets[1:]) if valid_sets else set()

    if not requested_period:
        return default_period

    if intersection and requested_period not in intersection:
        logger.warning(
            "Period '%s' is not valid for metrics %s (valid: %s). Using '%s'.",
            requested_period,
            metric_names,
            sorted(intersection),
            default_period,
        )
        return default_period

    return requested_period


def _clamp_since(
    since: datetime | None,
    until: datetime | None,
    metric_names: tuple[str, ...],
    config: dict,
) -> datetime | None:
    """Clamp since to the minimum allowed lookback across all requested metrics.

    Returns:
      - since unchanged if it is within the allowed range.
      - The earliest allowed date if since is too old but still before until.
      - None if the entire requested range is older than the lookback window,
        so _resolve_bounds falls back to the default rolling window.
    """
    if since is None:
        return None

    metrics_cfg = config.get("metrics", {})
    min_max_lookback = min(
        int(metrics_cfg.get(name, {}).get("max_lookback_days", 730))
        for name in metric_names
    )

    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    earliest_allowed = now - timedelta(days=min_max_lookback)

    if since < earliest_allowed:
        # If clamping since would push it past until, the whole range is out of
        # the available window — discard both dates and use the default window.
        if until is not None and earliest_allowed >= until:
            logger.warning(
                "Requested range (%s → %s) is entirely beyond max_lookback_days=%d. "
                "Using default %d-day rolling window instead.",
                since.date().isoformat(),
                until.date().isoformat(),
                min_max_lookback,
                metrics_cfg.get(metric_names[0], {}).get("window_days", 28),
            )
            return None

        logger.warning(
            "since=%s exceeds max_lookback_days=%d for metrics %s. Clamping to %s.",
            since.date().isoformat(),
            min_max_lookback,
            metric_names,
            earliest_allowed.date().isoformat(),
        )
        return earliest_allowed

    return since


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


def _parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_metric_total(payload: dict[str, Any], metric_name: str) -> int:
    for metric in payload.get("data", []):
        if metric.get("name") != metric_name:
            continue
        total_payload = metric.get("total_value") or {}
        if "value" in total_payload:
            return _normalize_value(total_payload.get("value"))
        values = metric.get("values") or []
        if values:
            return _normalize_value(values[-1].get("value", 0))
    return 0


def _extract_embedded_metric_total(embedded_insights: dict[str, Any] | None, metric_name: str) -> int:
    if not embedded_insights:
        return 0
    for metric in (embedded_insights.get("data") or []):
        if metric.get("name") != metric_name:
            continue
        values = metric.get("values") or []
        if values:
            return _normalize_value(values[-1].get("value", 0))
    return 0


def _media_type_label(media_type: str | None) -> str:
    mapping = {
        "IMAGE": "Image",
        "VIDEO": "Video",
        "CAROUSEL_ALBUM": "Carousel",
        "REEL": "Reel",
    }
    return mapping.get((media_type or "").upper(), "Post")


def _select_media_preview_url(
    media_type: str | None,
    media_url: str | None,
    thumbnail_url: str | None,
) -> str:
    """Select best preview URL for a media item.

    IG video/reel often provides thumbnail_url; image posts rely on media_url.
    """
    media_type_upper = (media_type or "").upper()
    media_url_value = (media_url or "").strip()
    thumbnail_url_value = (thumbnail_url or "").strip()

    if media_type_upper in {"VIDEO", "REEL"}:
        return thumbnail_url_value or media_url_value
    return media_url_value or thumbnail_url_value


def _post_title(caption: str | None, fallback: str) -> str:
    first_line = (caption or "").strip().splitlines()[0] if caption else ""
    if not first_line:
        return fallback
    if len(first_line) <= 38:
        return first_line
    return f"{first_line[:35].rstrip()}..."


async def _get_insights_by_metric_names(
    account_id: str,
    metric_names: tuple[str, ...],
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
    metric_type: str | None = "total_value",
) -> dict[str, dict]:
    if not metric_names:
        raise ValueError("Provide at least one metric name.")
    print(f"Fetching insights for account ID {account_id} with metrics={metric_names}, since={since}, until={until}, period={period}, metric_type={metric_type}")
    config = _load_config()
    route_template = config.get("routing", {}).get("insights_path")
    metric_cfg = config.get("metrics", {}).get(metric_names[0], {})
    resolved_period = _resolve_period_for_metrics(metric_names, period, config)
    window_days = int(metric_cfg.get("window_days", 28))
    since = _clamp_since(since, until, metric_names, config)
    print(f"Resolved period: {resolved_period}, clamped since: {since}, window_days: {window_days}")

    if not route_template:
        raise ValueError("Missing routing.insights_path in src/mcp_server/instagram/config.yaml")
    if window_days < 1:
        raise ValueError("metrics.reach.window_days must be at least 1")

    account = await get_account_by_id(account_id)
    if account is None:
        raise ValueError(f"Instagram account not found: {account_id}")
    print(f"Found Instagram account: {account.name} (ID: {account.id})")

    resolved_since, resolved_until = _resolve_bounds(since, until, window_days)
    insights_path = route_template.format(ig_user_id=account.id)
    client = get_client()
    request_started_at = time.perf_counter()
    request_params: dict[str, Any] = {
        "metric": ",".join(metric_names),
        "period": resolved_period,
        "since": int(resolved_since.timestamp()),
        "until": int(resolved_until.timestamp()),
    }
    print(f"Requesting insights with params: {request_params}")
    if metric_type is not None:
        request_params["metric_type"] = metric_type

    payload: dict[str, Any] = {}
    try:
        payload = await client.get(insights_path, **request_params)
    except Exception as exc:
        logger.warning("Error fetching insights: %s", exc)
        print(f"Error fetching insights: {exc}")
    # print(
    #     "instagram_insights_fetch duration_ms=%s account_id=%s metrics=%s period=%s since=%s until=%s",
    #     int((time.perf_counter() - request_started_at) * 1000),
    #     account_id,
    #     ",".join(metric_names),
    #     resolved_period,
    #     resolved_since.date().isoformat(),
    #     resolved_until.date().isoformat(),
    # )

    return {
        metric_name: _build_metric_summary(payload, metric_name, account, resolved_since, resolved_until, resolved_period)
        for metric_name in metric_names
    }


async def get_accounts(limit: int = 25) -> list[InstagramAccount]:
    """Return Instagram business accounts available to the configured token."""
    config = _load_config()
    route_template = config.get("routing", {}).get("accounts_path")
    account_fields = config.get("accounts", {}).get(
        "fields",
        "id,name,instagram_business_account{id,username,profile_picture_url}",
    )

    if not route_template:
        raise ValueError("Missing routing.accounts_path in src/mcp_server/instagram/config.yaml")

    client = get_client()
    accounts: list[InstagramAccount] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {
            "fields": account_fields,
            "limit": limit,
        }
        if cursor:
            params["after"] = cursor

        data = await client.get(route_template, **params)
        for item in data.get("data", []):
            account = InstagramAccount.from_api(item)
            if account is not None:
                accounts.append(account)

        paging = data.get("paging", {})
        cursors = paging.get("cursors", {})
        next_cursor = cursors.get("after")
        has_next = bool(paging.get("next"))

        if has_next and next_cursor:
            cursor = next_cursor
        else:
            break

    return accounts


async def get_accounts_field(*fields: str, limit: int = 25) -> list[Any]:
    """Helper to fetch one or more fields across all Instagram accounts."""
    if not fields:
        raise ValueError("Provide at least one field name.")

    accounts = await get_accounts(limit=limit)
    if len(fields) == 1:
        return [getattr(account, fields[0]) for account in accounts]
    return [{field: getattr(account, field) for field in fields} for account in accounts]


async def get_account_by_id(account_id: str) -> InstagramAccount | None:
    accounts = await get_accounts()
    return next((account for account in accounts if account.id == account_id), None)


async def get_reach_and_views_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
) -> dict[str, dict]:
    return await _get_insights_by_metric_names(
        account_id,
        ("reach", "views"),
        since=since,
        until=until,
        period=period,
    )


async def get_overview_metrics_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
) -> dict[str, dict]:
    return await _get_insights_by_metric_names(
        account_id,
        (
            "reach",
            "views",
            "total_interactions",
            "accounts_engaged",
            "follows_and_unfollows",
            "profile_links_taps",
        ),
        since=since,
        until=until,
        period=period,
    )


async def get_reach_timeseries_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str = "day",
) -> dict[str, dict]:
    config = _load_config()
    chart_route_template = (
        config.get("routing", {}).get("chart_insights_path")
        or config.get("routing", {}).get("insights_path")
    )
    reach_cfg = config.get("metrics", {}).get("reach", {})
    resolved_period = period or reach_cfg.get("period", "day")
    window_days = int(reach_cfg.get("window_days", 28))

    if not chart_route_template:
        raise ValueError("Missing routing.chart_insights_path in src/mcp_server/instagram/config.yaml")
    if window_days < 1:
        raise ValueError("metrics.reach.window_days must be at least 1")

    account = await get_account_by_id(account_id)
    if account is None:
        raise ValueError(f"Instagram account not found: {account_id}")

    resolved_since, resolved_until = _resolve_bounds(since, until, window_days)
    insights_path = chart_route_template.format(ig_user_id=account.id)
    client = get_client()
    request_started_at = time.perf_counter()
    print(f"Fetching reach timeseries for account ID {account_id} with since={since}, until={until}, period={period}")

    base_params: dict[str, Any] = {
        "metric": "reach",
        "period": resolved_period,
        "since": int(resolved_since.timestamp()),
        "until": int(resolved_until.timestamp()),
    }
    initial_payload = await client.get(insights_path, **base_params)
    print(
        "instagram_reach_chart_fetch duration_ms=%s account_id=%s period=%s since=%s until=%s",
        int((time.perf_counter() - request_started_at) * 1000),
        account_id,
        resolved_period,
        resolved_since.date().isoformat(),
        resolved_until.date().isoformat(),
    )
    initial_result = {
        "reach": _build_metric_summary(initial_payload, "reach", account, resolved_since, resolved_until, resolved_period)
    }

    logger.debug(
        "instagram_reach_chart_fetch duration_ms=%s account_id=%s period=%s since=%s until=%s",
        int((time.perf_counter() - request_started_at) * 1000),
        account_id,
        resolved_period,
        resolved_since.date().isoformat(),
        resolved_until.date().isoformat(),
    )

    if (initial_result.get("reach") or {}).get("spark"):
        return initial_result

    fallback_payload = await client.get(insights_path, **{**base_params, "metric_type": "time_series"})
    fallback_result = {
        "reach": _build_metric_summary(fallback_payload, "reach", account, resolved_since, resolved_until, resolved_period)
    }
    if (fallback_result.get("reach") or {}).get("spark"):
        return fallback_result

    return initial_result


async def get_reach_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
) -> dict:
    """Return summarized reach analytics for an Instagram business account."""
    print(f"Fetching reach insights for account ID {account_id} with since={since}, until={until}, period={period}")
    return (await _get_insights_by_metric_names(account_id, ("reach",), since=since, until=until, period=period))["reach"]


async def get_views_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    period: str | None = None,
) -> dict:
    """Return summarized views analytics for an Instagram business account."""
    print(f"Fetching views insights for account ID {account_id} with since={since}, until={until}, period={period}")
    return (await _get_insights_by_metric_names(account_id, ("views",), since=since, until=until, period=period))["views"]


async def get_engagement_breakdown_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Return Instagram engagement breakdown totals for donut rendering."""
    metrics = (
        "total_interactions",
        "likes",
        "comments",
        "saves",
        "shares",
        "reposts",
        "replies",
    )
    summaries = await _get_insights_by_metric_names(
        account_id,
        metrics,
        since=since,
        until=until,
        period="day",
        metric_type="total_value",
    )

    total_interactions = _non_negative_int((summaries.get("total_interactions") or {}).get("total_count", 0))
    likes = _non_negative_int((summaries.get("likes") or {}).get("total_count", 0))
    comments = _non_negative_int((summaries.get("comments") or {}).get("total_count", 0))
    saves = _non_negative_int((summaries.get("saves") or {}).get("total_count", 0))
    shares = _non_negative_int((summaries.get("shares") or {}).get("total_count", 0))
    reposts = _non_negative_int((summaries.get("reposts") or {}).get("total_count", 0))
    replies = _non_negative_int((summaries.get("replies") or {}).get("total_count", 0))
    print(
        f"Engagement breakdown for account ID {account_id} with since={since}, until={until}: "
        f"total_interactions={total_interactions}, likes={likes}, comments={comments}, saves={saves}, "
        f"shares={shares}, reposts={reposts}, replies={replies}"
    )

    known_sum = likes + comments + saves + shares + reposts + replies
    other = max(total_interactions - known_sum, 0)
    print(
        f"Calculated engagement breakdown for account ID {account_id}: known_sum={known_sum}, other={other}"
    )

    breakdown = {
        "likes": likes,
        "comments": comments,
        "saves": saves,
        "shares": shares,
        "reposts": reposts,
        "replies": replies,
        "other": other,
    }

    return {
        "account_id": account_id,
        "metric": "engagement_breakdown",
        "total_interactions": total_interactions,
        "components_sum": known_sum,
        "breakdown": breakdown,
        "since": (summaries.get("total_interactions") or {}).get("since"),
        "until": (summaries.get("total_interactions") or {}).get("until"),
    }


async def get_top_posts_by_account_id(
    account_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return top Instagram media posts ranked by engagement_total."""
    config = _load_config()
    account = await get_account_by_id(account_id)
    if account is None:
        raise ValueError(f"Instagram account not found: {account_id}")

    should_filter_by_window = since is not None or until is not None
    resolved_since: datetime | None = None
    resolved_until: datetime | None = None
    if should_filter_by_window:
        resolved_since, resolved_until = _resolve_bounds(since, until, window_days=28)
    media_route_template = config.get("routing", {}).get("media_path", "/{ig_user_id}/media")
    media_path = media_route_template.format(ig_user_id=account.id)
    posts_cfg = config.get("posts", {})
    media_fields = posts_cfg.get(
        "media_fields",
        "id,caption,media_type,timestamp,thumbnail_url,media_url,permalink,insights.metric(reach,total_interactions)",
    )
    configured_limit = int(posts_cfg.get("default_limit", 10))
    effective_limit = max(int(limit or configured_limit), 1)

    client = get_client()
    media_payload = await client.get(media_path, fields=media_fields, limit=effective_limit)

    ranked_posts: list[dict[str, Any]] = []
    for item in media_payload.get("data", []):
        created_at = _parse_graph_datetime(item.get("timestamp"))
        if created_at is None:
            continue
        if should_filter_by_window and resolved_since is not None and resolved_until is not None:
            if created_at < resolved_since or created_at >= resolved_until:
                continue

        media_id = item.get("id")
        reach_total = _extract_embedded_metric_total(item.get("insights"), "reach")
        interactions_total = _extract_embedded_metric_total(item.get("insights"), "total_interactions")
        engagement_total = interactions_total
        engagement_rate = round((engagement_total / reach_total) * 100, 2) if reach_total > 0 else None

        fallback_title = f"Instagram post · {created_at.date().isoformat()}"
        preview_url = _select_media_preview_url(
            item.get("media_type"),
            item.get("media_url"),
            item.get("thumbnail_url"),
        )
        ranked_posts.append(
            {
                "id": media_id,
                "title": _post_title(item.get("caption"), fallback_title),
                "created_at": created_at.isoformat(),
                "type": _media_type_label(item.get("media_type")),
                "reach": reach_total,
                "engagement_total": engagement_total,
                "engagement_rate": engagement_rate,
                "thumbnail_url": preview_url,
                "media_url": (item.get("media_url") or "").strip(),
                "permalink_url": item.get("permalink") or "",
                "reach_label": _format_compact(reach_total),
                "engagement_label": _format_compact(engagement_total),
            }
        )

    ranked_posts.sort(
        key=lambda post: (
            int(post.get("engagement_total", 0) or 0),
            int(post.get("reach", 0) or 0),
            post.get("created_at", ""),
        ),
        reverse=True,
    )

    return ranked_posts[:effective_limit]


async def get_all_posts_by_account_id(account_id: str) -> list[dict[str, Any]]:
    """Return all Instagram media posts (lifetime) for one account."""
    config = _load_config()
    account = await get_account_by_id(account_id)
    if account is None:
        raise ValueError(f"Instagram account not found: {account_id}")

    media_route_template = config.get("routing", {}).get("media_path", "/{ig_user_id}/media")
    media_path = media_route_template.format(ig_user_id=account.id)
    posts_cfg = config.get("posts", {})
    media_fields = posts_cfg.get(
        "media_fields",
        "id,caption,media_type,timestamp,thumbnail_url,media_url,permalink,insights.metric(reach,total_interactions)",
    )
    page_limit = max(int(posts_cfg.get("default_limit", 25)), 25)

    client = get_client()
    cursor: str | None = None
    all_posts: list[dict[str, Any]] = []

    while True:
        request_params: dict[str, Any] = {
            "fields": media_fields,
            "limit": page_limit,
        }
        if cursor:
            request_params["after"] = cursor

        media_payload = await client.get(media_path, **request_params)

        for item in media_payload.get("data", []):
            created_at = _parse_graph_datetime(item.get("timestamp"))
            if created_at is None:
                continue

            media_id = item.get("id")
            reach_total = _extract_embedded_metric_total(item.get("insights"), "reach")
            interactions_total = _extract_embedded_metric_total(item.get("insights"), "total_interactions")
            engagement_total = interactions_total
            engagement_rate = round((engagement_total / reach_total) * 100, 2) if reach_total > 0 else None

            fallback_title = f"Instagram post · {created_at.date().isoformat()}"
            preview_url = _select_media_preview_url(
                item.get("media_type"),
                item.get("media_url"),
                item.get("thumbnail_url"),
            )
            all_posts.append(
                {
                    "id": media_id,
                    "title": _post_title(item.get("caption"), fallback_title),
                    "created_at": created_at.isoformat(),
                    "type": _media_type_label(item.get("media_type")),
                    "reach": reach_total,
                    "engagement_total": engagement_total,
                    "engagement_rate": engagement_rate,
                    "thumbnail_url": preview_url,
                    "media_url": (item.get("media_url") or "").strip(),
                    "permalink_url": item.get("permalink") or "",
                    "reach_label": _format_compact(reach_total),
                    "engagement_label": _format_compact(engagement_total),
                }
            )

        paging = media_payload.get("paging", {})
        cursors = paging.get("cursors", {})
        next_cursor = cursors.get("after")
        has_next = bool(paging.get("next"))

        if has_next and next_cursor:
            cursor = next_cursor
        else:
            break

    all_posts.sort(key=lambda post: post.get("created_at", ""), reverse=True)
    return all_posts


async def get_posts_metrics_by_account_id(account_id: str) -> list[dict[str, Any]]:
    """Return lifetime Instagram post metrics using media-level count fields.

    Graph API shape:
    /{ig_user_id}/media?fields=id,caption,media_type,media_product_type,total_views_count,total_like_count,comments_count,shares_count,reposts_count,saved_count,thumbnail_url,media_url
    """
    config = _load_config()
    account = await get_account_by_id(account_id)
    if account is None:
        raise ValueError(f"Instagram account not found: {account_id}")

    media_route_template = config.get("routing", {}).get("media_path", "/{ig_user_id}/media")
    media_path = media_route_template.format(ig_user_id=account.id)
    requested_fields = (
        "id,caption,media_type,media_product_type,total_views_count,total_like_count,comments_count,"
        "shares_count,reposts_count,saved_count,thumbnail_url,media_url,timestamp"
    )

    client = get_client()
    cursor: str | None = None
    page_limit = 50
    all_posts: list[dict[str, Any]] = []

    while True:
        request_params: dict[str, Any] = {
            "fields": requested_fields,
            "limit": page_limit,
        }
        if cursor:
            request_params["after"] = cursor

        media_payload = await client.get(media_path, **request_params)

        for item in media_payload.get("data", []):
            created_at = _parse_graph_datetime(item.get("timestamp"))

            views = _normalize_value(item.get("total_views_count"))
            likes = _normalize_value(item.get("total_like_count"))
            comments = _normalize_value(item.get("comments_count"))
            shares = _normalize_value(item.get("shares_count"))
            reposts = _normalize_value(item.get("reposts_count"))
            saves = _normalize_value(item.get("saved_count"))

            engagement_total = max(likes + comments + shares + reposts + saves, 0)
            engagement_rate = round((engagement_total / views) * 100, 2) if views > 0 else None

            fallback_title = (
                f"Instagram post · {created_at.date().isoformat()}"
                if created_at is not None
                else "Instagram post"
            )
            media_type_value = item.get("media_type") or item.get("media_product_type")
            preview_url = _select_media_preview_url(
                media_type_value,
                item.get("media_url"),
                item.get("thumbnail_url"),
            )

            all_posts.append(
                {
                    "id": item.get("id"),
                    "title": _post_title(item.get("caption"), fallback_title),
                    "created_at": created_at.isoformat() if created_at else None,
                    "type": _media_type_label(media_type_value),
                    "reach": views,
                    "engagement_total": engagement_total,
                    "engagement_rate": engagement_rate,
                    "thumbnail_url": preview_url,
                    "media_url": (item.get("media_url") or "").strip(),
                    "reach_label": _format_compact(views),
                    "engagement_label": _format_compact(engagement_total),
                    "view_count": views,
                    "like_count": likes,
                    "comments_count": comments,
                    "shares_count": shares,
                    "reposts_count": reposts,
                    "saved_count": saves,
                }
            )

        paging = media_payload.get("paging", {})
        cursors = paging.get("cursors", {})
        next_cursor = cursors.get("after")
        has_next = bool(paging.get("next"))

        if has_next and next_cursor:
            cursor = next_cursor
        else:
            break

    all_posts.sort(key=lambda post: post.get("created_at") or "", reverse=True)
    return all_posts


# ---------------------------------------------------------------------------
# Audience demographics
# ---------------------------------------------------------------------------

def _extract_breakdown_payload(payload: dict, metric_name: str) -> tuple[list[str], list[dict]]:
    """Return dimension keys and flattened result rows from insights demographics payload."""
    for metric in (payload.get("data") or []):
        if metric.get("name") != metric_name:
            continue

        total_value = metric.get("total_value") or {}
        breakdowns = total_value.get("breakdowns") or []
        if not breakdowns:
            return [], []

        all_rows: list[dict] = []
        dimension_keys: list[str] = []
        for breakdown in breakdowns:
            keys = [str(k).lower() for k in (breakdown.get("dimension_keys") or [])]
            if not dimension_keys and keys:
                dimension_keys = keys
            all_rows.extend(breakdown.get("results") or [])

        return dimension_keys, all_rows

    return [], []


_AGE_BUCKET_MAP: dict[str, str] = {
    "13-17": "13-24",
    "18-24": "13-24",
    "25-34": "25-34",
    "35-44": "35-44",
    "45-54": "45-54",
    "55-64": "55+",
    "65+":   "55+",
}

_GENDER_LABEL_MAP: dict[str, str] = {
    "F": "Female",
    "M": "Male",
    "U": "Unknown",
}


async def get_audience_demographics_by_account_id(account_id: str) -> dict[str, Any]:
    """Return lifetime engaged audience demographics (age, country, gender, gender-by-age)."""
    config = _load_config()
    route_template = config.get("routing", {}).get("insights_path")
    if not route_template:
        raise ValueError("Missing routing.insights_path in src/mcp_server/instagram/config.yaml")

    account = await get_account_by_id(account_id)
    if account is None:
        raise ValueError(f"Instagram account not found: {account_id}")

    insights_path = route_template.format(ig_user_id=account.id)
    client = get_client()
    demo_metric = "engaged_audience_demographics"

    payload = await client.get(
        insights_path,
        metric=demo_metric,
        period="lifetime",
        timeframe="this_month",
        breakdown="age,country,gender",
        metric_type="total_value",
    )

    dimension_keys, result_rows = _extract_breakdown_payload(payload, demo_metric)
    age_idx = dimension_keys.index("age") if "age" in dimension_keys else 0
    country_idx = dimension_keys.index("country") if "country" in dimension_keys else 1
    gender_idx = dimension_keys.index("gender") if "gender" in dimension_keys else 2

    # ── Age (grouped into 5 buckets) ──────────────────────────────────────
    age_buckets: dict[str, int] = {"13-24": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55+": 0}
    for item in result_rows:
        dims = item.get("dimension_values") or []
        raw_age = dims[age_idx] if age_idx < len(dims) else "unknown"
        bucket = _AGE_BUCKET_MAP.get(raw_age)
        if bucket:
            age_buckets[bucket] += int(item.get("value") or 0)

    # ── Country (top 9 + Other) ───────────────────────────────────────────
    country_counts: dict[str, int] = {}
    for item in result_rows:
        dims = item.get("dimension_values") or []
        code = dims[country_idx] if country_idx < len(dims) else "unknown"
        country_counts[code] = country_counts.get(code, 0) + int(item.get("value") or 0)
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    top_countries: dict[str, int] = dict(sorted_countries[:9])
    other_country_count = sum(v for _, v in sorted_countries[9:])
    if other_country_count > 0:
        top_countries["Other"] = other_country_count

    # ── Gender ────────────────────────────────────────────────────────────
    gender_counts: dict[str, int] = {}
    for item in result_rows:
        dims = item.get("dimension_values") or []
        code = dims[gender_idx] if gender_idx < len(dims) else "U"
        label = _GENDER_LABEL_MAP.get(code, code)
        gender_counts[label] = gender_counts.get(label, 0) + int(item.get("value") or 0)

    # ── Gender by Age group ───────────────────────────────────────────────
    age_gender: dict[str, dict[str, int]] = {
        b: {"Female": 0, "Male": 0, "Unknown": 0}
        for b in ["13-24", "25-34", "35-44", "45-54", "55+"]
    }
    for item in result_rows:
        dims = item.get("dimension_values") or []
        if not dims:
            continue
        raw_age = dims[age_idx] if age_idx < len(dims) else None
        gender_code = dims[gender_idx] if gender_idx < len(dims) else "U"
        if not raw_age:
            continue
        bucket = _AGE_BUCKET_MAP.get(raw_age)
        if not bucket:
            continue
        gender_label = _GENDER_LABEL_MAP.get(gender_code, gender_code)
        age_gender[bucket][gender_label] = age_gender[bucket].get(gender_label, 0) + int(item.get("value") or 0)

    return {
        "account_id": account_id,
        "scope": "lifetime",
        "age": age_buckets,
        "country": top_countries,
        "gender": gender_counts,
        "age_gender": age_gender,
    }
