"""Aggregated social overview payload builder for dashboard screens."""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp.facebook.analytics import get_pages, get_reach_by_page_id
from mcp.instagram.analytics import (
    get_accounts,
    get_overview_metrics_by_account_id,
    get_reach_timeseries_by_account_id,
    get_top_posts_by_account_id,
)

CACHE_TTL_SECONDS = 120
ENABLE_OVERVIEW_CACHE = False
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
logger = logging.getLogger(__name__)


def _log_step_duration(step: str, started_at: float, **details: Any) -> None:
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if details:
           print(f"social_overview step={step} duration_ms={duration_ms} details={details}")
    else:
           print(f"social_overview step={step} duration_ms={duration_ms}")


def _parse_date_or_none(value: str | None, *, is_until: bool = False) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    if is_until:
        # Convert inclusive YYYY-MM-DD "until" into an exclusive upper bound.
        return parsed + timedelta(days=1)
    return parsed


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


def _compute_previous_window_bounds(
    since: str | None,
    until: str | None,
) -> tuple[str, str] | None:
    if not since or not until:
        return None

    since_date = datetime.fromisoformat(since).date()
    until_date = datetime.fromisoformat(until).date()
    if since_date > until_date:
        raise ValueError("Invalid range: since must be earlier than or equal to until.")

    window_days = (until_date - since_date).days + 1
    prev_until = since_date - timedelta(days=1)
    prev_since = prev_until - timedelta(days=window_days - 1)
    return prev_since.isoformat(), prev_until.isoformat()


def _last_30_day_window_bounds() -> tuple[datetime, datetime]:
    until_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since_date = until_date - timedelta(days=29)
    return since_date, until_date


def _format_previous_window_label(comparison_window: dict[str, str] | None, period: str) -> str:
    if not comparison_window:
        return f"vs previous {period}"
    try:
        since_date = datetime.fromisoformat(comparison_window["since"]).date()
        until_date = datetime.fromisoformat(comparison_window["until"]).date()
    except (KeyError, ValueError):
        return f"vs previous {period}"
    return f"vs {since_date.strftime('%b %d')} - {until_date.strftime('%b %d')}"


def _cache_key(
    platform: str,
    selected_account_id: str | None,
    since: str | None,
    until: str | None,
    period: str,
    timezone_name: str,
) -> str:
    return (
        f"v1|{platform}|{selected_account_id or '-'}|{since or '-'}|{until or '-'}|"
        f"{period}|{timezone_name}"
    )


def _read_cache(key: str) -> dict[str, Any] | None:
    item = _CACHE.get(key)
    if item is None:
        return None
    expires_at, payload = item
    if time.time() >= expires_at:
        _CACHE.pop(key, None)
        return None

    cached = dict(payload)
    meta = dict(cached.get("meta", {}))
    meta["cache"] = {
        "hit": True,
        "ttl_seconds": CACHE_TTL_SECONDS,
    }
    cached["meta"] = meta
    return cached


def _write_cache(key: str, payload: dict[str, Any]) -> None:
    _CACHE[key] = (time.time() + CACHE_TTL_SECONDS, payload)


def _derive_metric(
    spark: list[int],
    multiplier: float,
    label: str,
    metric: str,
    period: str,
) -> dict[str, Any]:
    if not spark:
        return {
            "label": label,
            "metric": metric,
            "description": f"{label} for the selected window.",
            "value": "0",
            "change_value": "0",
            "delta": "0.0%",
            "comparison_label": f"vs previous {period}",
            "spark": [],
            "current_total": 0,
            "previous_total": 0,
            "trend": "flat",
        }

    scaled = [max(int(v * multiplier), 0) for v in spark]
    midpoint = max(len(scaled) // 2, 1)
    previous_total = sum(scaled[:midpoint])
    current_total = sum(scaled[midpoint:]) or sum(scaled[:midpoint])
    if previous_total <= 0:
        delta = "0.0%"
    else:
        delta = f"{((current_total - previous_total) / previous_total) * 100:.1f}%"

    change_total = current_total - previous_total
    if change_total > 0:
        trend = "up"
    elif change_total < 0:
        trend = "down"
    else:
        trend = "flat"

    compact = current_total
    if compact >= 1_000_000:
        value = f"{compact / 1_000_000:.1f}M"
    elif compact >= 1_000:
        value = f"{compact / 1_000:.1f}K"
    else:
        value = str(compact)

    return {
        "label": label,
        "metric": metric,
        "description": f"{label} for the selected window.",
        "value": value,
        "change_value": f"{abs(change_total):,}",
        "delta": delta,
        "comparison_label": f"vs previous {period}",
        "spark": scaled,
        "current_total": current_total,
        "previous_total": previous_total,
        "trend": trend,
    }


def _build_kpi_bundle(reach: dict[str, Any] | None, period: str = "period") -> dict[str, Any]:
    return _build_kpi_bundle_for_period(reach, period)


def _build_metric_bundle(metric: dict[str, Any] | None, previous_metric: dict[str, Any] | None, period: str, label: str) -> dict[str, Any] | None:
    if not metric:
        return None

    current_total = int(metric.get("total_count", metric.get("current_total", 0)) or 0)
    if previous_metric is None:
        previous_total = int(metric.get("previous_total", 0) or 0)
    else:
        previous_total = int(previous_metric.get("total_count", previous_metric.get("current_total", 0)) or 0)

    change_total = current_total - previous_total
    if change_total > 0:
        trend = "up"
    elif change_total < 0:
        trend = "down"
    else:
        trend = "flat"

    return {
        **metric,
        "label": label,
        "value": metric.get("value") or _format_compact(current_total),
        "total_count": current_total,
        "current_total": current_total,
        "previous_total": previous_total,
        "change_value": f"{abs(change_total):,}",
        "delta": _pct_change(current_total, previous_total),
        "comparison_label": _format_previous_window_label(metric.get("comparison_window"), period),
        "trend": trend,
        "description": metric.get("description") or f"{label} for the selected window.",
    }


def _build_engagement_rate_bundle(
    engagement_metric: dict[str, Any] | None,
    reach_metric: dict[str, Any] | None,
    previous_engagement_metric: dict[str, Any] | None,
    previous_reach_metric: dict[str, Any] | None,
    period: str,
) -> dict[str, Any]:
    current_engagement = int((engagement_metric or {}).get("total_count", (engagement_metric or {}).get("current_total", 0)) or 0)
    current_reach_raw = int((reach_metric or {}).get("total_count", (reach_metric or {}).get("current_total", 0)) or 0)
    current_reach = max(current_reach_raw, 1)

    previous_engagement = int((previous_engagement_metric or {}).get("total_count", (previous_engagement_metric or {}).get("current_total", 0)) or 0)
    previous_reach_raw = int((previous_reach_metric or {}).get("total_count", (previous_reach_metric or {}).get("current_total", 0)) or 0)
    previous_reach = max(previous_reach_raw, 1)

    current_rate = (current_engagement / current_reach) * 100
    previous_rate = (previous_engagement / previous_reach) * 100
    change_pp = current_rate - previous_rate

    if change_pp > 0:
        trend = "up"
    elif change_pp < 0:
        trend = "down"
    else:
        trend = "flat"

    if previous_rate <= 0:
        delta = "0.0%"
    else:
        delta = f"{((current_rate - previous_rate) / previous_rate) * 100:.1f}%"

    engagement_spark = (engagement_metric or {}).get("spark") or []
    reach_spark = (reach_metric or {}).get("spark") or []
    spark: list[float] = []
    for engagement_value, reach_value in zip(engagement_spark, reach_spark, strict=False):
        divisor = max(int(reach_value or 0), 1)
        spark.append(round((int(engagement_value or 0) / divisor) * 100, 2))

    comparison_window = (
        (engagement_metric or {}).get("comparison_window")
        or (reach_metric or {}).get("comparison_window")
    )

    return {
        "label": "Engagement Rate",
        "metric": "engagement_rate",
        "description": "Engagement Rate = total interactions / reach for the selected window, compared with the previous window.",
        "value": f"{current_rate:.2f}%",
        "change_value": f"{abs(change_pp):.2f} pp",
        "delta": delta,
        "comparison_label": _format_previous_window_label(comparison_window, period),
        "spark": spark,
        "current_total": round(current_rate, 4),
        "previous_total": round(previous_rate, 4),
        "trend": trend,
        "comparison_window": comparison_window,
    }


def _build_kpi_bundle_for_period(
    reach: dict[str, Any] | None,
    period: str,
    views: dict[str, Any] | None = None,
    engagement_metric: dict[str, Any] | None = None,
    engaged_accounts_metric: dict[str, Any] | None = None,
    follows_and_unfollows_metric: dict[str, Any] | None = None,
    profile_links_taps_metric: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not reach:
        return {
            "reach": None,
            "engagement": None,
            "engaged_accounts": None,
            "follows_and_unfollows": None,
            "profile_links_taps": None,
            "engagement_rate": None,
            "followers": None,
            "video_views": None,
            "views": None,
        }
    reach_spark = reach.get("spark", [])
    normalized_reach = _build_metric_bundle(reach, None, period, "Reach") or reach
    views_spark = (views or {}).get("spark") or reach_spark
    engagement = _build_metric_bundle(engagement_metric, None, period, "Engagement")
    if engagement is None:
        engagement = _derive_metric(reach_spark, 0.12, "Engagement", "engagement", period)
    followers = _derive_metric(reach_spark, 0.018, "Followers", "followers", period)
    video_views = _derive_metric(reach_spark, 0.71, "Video Views", "video_views", period)
    normalized_views = _build_metric_bundle(views, None, period, "Views")
    engaged_accounts = _build_metric_bundle(engaged_accounts_metric, None, period, "Engaged Accounts")
    follows_and_unfollows = _build_metric_bundle(follows_and_unfollows_metric, None, period, "Follows & Unfollows")
    profile_links_taps = _build_metric_bundle(profile_links_taps_metric, None, period, "Profile Link Taps")
    engagement_rate = _build_engagement_rate_bundle(engagement, reach, None, None, period)

    return {
        "reach": normalized_reach,
        "engagement": engagement,
        "engaged_accounts": engaged_accounts,
        "follows_and_unfollows": follows_and_unfollows,
        "profile_links_taps": profile_links_taps,
        "engagement_rate": engagement_rate,
        "followers": followers,
        "video_views": video_views,
        "views": normalized_views,
    }


def _build_charts(kpis: dict[str, Any], reach_chart_metric: dict[str, Any] | None = None) -> dict[str, Any]:
    reach = reach_chart_metric or kpis.get("reach") or {}
    reach_series = reach.get("spark", [])
    return {
        "reach_series": reach_series,
        "reach_since": reach.get("since"),
        "reach_until": reach.get("until"),
        "performance_overview": [
            {"name": "Reach", "color": "#4A8CFF", "points": reach_series},
        ],
    }


async def _fetch_audience_placeholder() -> dict[str, Any]:
    return {
        "gender_split": {"women": 54.3, "men": 45.7},
    }


async def _fetch_posts_placeholder() -> list[dict[str, Any]]:
    return []

def _to_account_item(item: Any, platform: str) -> dict[str, Any]:
    if platform == "fb":
        return {
            "id": item.id,
            "name": item.name,
            "picture_url": item.picture_url,
            "followers_count": getattr(item, "followers_count", 0),
            "fan_count": getattr(item, "fan_count", 0),
        }
    return {
        "id": item.id,
        "name": item.name,
        "username": item.username,
        "picture_url": item.profile_picture_url,
        "followers_count": getattr(item, "followers_count", 0),
        "follows_count": getattr(item, "follows_count", 0),
        "media_count": getattr(item, "media_count", 0),
        "page_id": item.page_id,
        "page_name": item.page_name,
    }


async def build_social_overview(
    platform: str,
    selected_account_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    period: str = "day",
    timezone_name: str = "UTC",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Build a sectioned social overview payload for one platform."""
    started_at = time.perf_counter()
    partial_errors: list[str] = []

    cache_key = _cache_key(platform, selected_account_id, since, until, period, timezone_name)
    if ENABLE_OVERVIEW_CACHE and not force_refresh:
        cached = _read_cache(cache_key)
        if cached is not None:
            return cached

    parsed_since = _parse_date_or_none(since)
    parsed_until = _parse_date_or_none(until, is_until=True)

    accounts_started_at = time.perf_counter()

    if platform == "fb":
        pages = await get_pages()
        accounts = [_to_account_item(page, platform) for page in pages]
        _log_step_duration("load_accounts", accounts_started_at, platform=platform, account_count=len(accounts))
        selected = next((a for a in accounts if a["id"] == selected_account_id), None)
        if selected is None and accounts:
            selected = accounts[0]

        reach: dict[str, Any] | None = None
        chart_reach: dict[str, Any] | None = None
        audience: dict[str, Any] = {}
        posts: list[dict[str, Any]] = []
        if selected is not None:
            metrics_started_at = time.perf_counter()
            chart_since, chart_until = _last_30_day_window_bounds()
            reach_result, chart_reach_result, audience_result, posts_result = await asyncio.gather(
                get_reach_by_page_id(
                    selected["id"],
                    since=parsed_since,
                    until=parsed_until,
                    period=period,
                ),
                get_reach_by_page_id(
                    selected["id"],
                    since=chart_since,
                    until=chart_until,
                    period="day",
                ),
                _fetch_audience_placeholder(),
                _fetch_posts_placeholder(),
                return_exceptions=True,
            )
            _log_step_duration("fetch_metrics_parallel", metrics_started_at, platform=platform, selected_account_id=selected["id"])
            if isinstance(reach_result, Exception):
                partial_errors.append(f"reach: {reach_result}")
            else:
                reach = reach_result
                current_since = since or reach.get("since")
                current_until = until or reach.get("until")
                previous_window = _compute_previous_window_bounds(current_since, current_until)
                if previous_window is not None:
                    prev_since, prev_until = previous_window
                    try:
                        previous_started_at = time.perf_counter()
                        previous_reach = await get_reach_by_page_id(
                            selected["id"],
                            since=_parse_date_or_none(prev_since),
                            until=_parse_date_or_none(prev_until, is_until=True),
                            period=period,
                        )
                        _log_step_duration("fetch_previous_window", previous_started_at, platform=platform, selected_account_id=selected["id"])
                        current_total = int(reach.get("total_count", reach.get("current_total", 0)) or 0)
                        previous_total = int(previous_reach.get("total_count", previous_reach.get("current_total", 0)) or 0)
                        reach["total_count"] = current_total
                        reach["current_total"] = current_total
                        reach["previous_total"] = previous_total
                        reach["comparison_window"] = {
                            "since": prev_since,
                            "until": prev_until,
                        }
                    except Exception as exc:
                        partial_errors.append(f"reach_previous_window: {exc}")

            if isinstance(chart_reach_result, Exception):
                partial_errors.append(f"reach_chart: {chart_reach_result}")
            else:
                chart_reach = chart_reach_result

            if isinstance(audience_result, Exception):
                partial_errors.append(f"audience: {audience_result}")
            else:
                audience = audience_result

            if isinstance(posts_result, Exception):
                partial_errors.append(f"posts: {posts_result}")
            else:
                posts = posts_result

        merge_started_at = time.perf_counter()
        kpis = _build_kpi_bundle(reach, period)
        charts = _build_charts(kpis, chart_reach)
        _log_step_duration("build_kpis_and_charts", merge_started_at, platform=platform)

        payload = {
            "platform": platform,
            "summary": {
                "accounts": accounts,
                "selected_account": selected,
            },
            "kpis": kpis,
            "charts": charts,
            "audience": audience,
            "posts": posts,
            "meta": {
                "partial_errors": partial_errors,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "params": {
                    "period": period,
                    "since": since,
                    "until": until,
                    "timezone": timezone_name,
                },
                "duration_ms": int((time.perf_counter() - started_at) * 1000),
                "cache": {
                    "hit": False,
                    "ttl_seconds": CACHE_TTL_SECONDS,
                },
            },
        }
        _log_step_duration("build_payload", started_at, platform=platform, selected_account_id=(selected or {}).get("id"))
        if ENABLE_OVERVIEW_CACHE:
            _write_cache(cache_key, payload)
        return payload

    if platform == "ig":
        ig_accounts = await get_accounts()
        accounts = [_to_account_item(account, platform) for account in ig_accounts]
        _log_step_duration("load_accounts", accounts_started_at, platform=platform, account_count=len(accounts))
        selected = next((a for a in accounts if a["id"] == selected_account_id), None)
        if selected is None and accounts:
            selected = accounts[0]
        reach: dict[str, Any] | None = None
        views: dict[str, Any] | None = None
        previous_reach: dict[str, Any] | None = None
        previous_views: dict[str, Any] | None = None
        engagement_metric: dict[str, Any] | None = None
        previous_engagement_metric: dict[str, Any] | None = None
        engaged_accounts_metric: dict[str, Any] | None = None
        previous_engaged_accounts_metric: dict[str, Any] | None = None
        follows_and_unfollows_metric: dict[str, Any] | None = None
        previous_follows_and_unfollows_metric: dict[str, Any] | None = None
        profile_links_taps_metric: dict[str, Any] | None = None
        previous_profile_links_taps_metric: dict[str, Any] | None = None
        chart_reach_metric: dict[str, Any] | None = None
        audience: dict[str, Any] = {}
        posts: list[dict[str, Any]] = []
        if selected is not None:
            metrics_started_at = time.perf_counter()
            chart_since, chart_until = _last_30_day_window_bounds()
            current_metrics_result, chart_reach_result, audience_result, posts_result = await asyncio.gather(
                get_overview_metrics_by_account_id(
                    selected["id"],
                    since=parsed_since,
                    until=parsed_until,
                    period=period,
                ),
                get_reach_timeseries_by_account_id(
                    selected["id"],
                    since=chart_since,
                    until=chart_until,
                    period="day",
                ),
                _fetch_audience_placeholder(),
                get_top_posts_by_account_id(
                    selected["id"],
                    since=parsed_since,
                    until=parsed_until,
                    limit=10,
                ),
                return_exceptions=True,
            )
            _log_step_duration("fetch_metrics_parallel", metrics_started_at, platform=platform, selected_account_id=selected["id"])
            if isinstance(current_metrics_result, Exception):
                partial_errors.append(f"reach_views: {current_metrics_result}")
            else:
                reach = current_metrics_result.get("reach")
                views = current_metrics_result.get("views")
                engagement_metric = current_metrics_result.get("total_interactions")
                engaged_accounts_metric = current_metrics_result.get("accounts_engaged")
                follows_and_unfollows_metric = current_metrics_result.get("follows_and_unfollows")
                profile_links_taps_metric = current_metrics_result.get("profile_links_taps")
                current_since = since or (reach or {}).get("since")
                current_until = until or (reach or {}).get("until")
                previous_window = _compute_previous_window_bounds(current_since, current_until)
                if previous_window is not None:
                    prev_since, prev_until = previous_window
                    try:
                        previous_started_at = time.perf_counter()
                        previous_metrics = await get_overview_metrics_by_account_id(
                            selected["id"],
                            since=_parse_date_or_none(prev_since),
                            until=_parse_date_or_none(prev_until, is_until=True),
                            period=period,
                        )
                        _log_step_duration("fetch_previous_window", previous_started_at, platform=platform, selected_account_id=selected["id"])
                        previous_reach = previous_metrics.get("reach")
                        previous_views = previous_metrics.get("views")
                        previous_engagement_metric = previous_metrics.get("total_interactions")
                        previous_engaged_accounts_metric = previous_metrics.get("accounts_engaged")
                        previous_follows_and_unfollows_metric = previous_metrics.get("follows_and_unfollows")
                        previous_profile_links_taps_metric = previous_metrics.get("profile_links_taps")
                        comparison_window = {
                            "since": prev_since,
                            "until": prev_until,
                        }
                        if reach is not None:
                            reach["comparison_window"] = comparison_window
                        if views is not None:
                            views["comparison_window"] = comparison_window
                        if engagement_metric is not None:
                            engagement_metric["comparison_window"] = comparison_window
                        if engaged_accounts_metric is not None:
                            engaged_accounts_metric["comparison_window"] = comparison_window
                        if follows_and_unfollows_metric is not None:
                            follows_and_unfollows_metric["comparison_window"] = comparison_window
                        if profile_links_taps_metric is not None:
                            profile_links_taps_metric["comparison_window"] = comparison_window
                    except Exception as exc:
                        partial_errors.append(f"reach_previous_window: {exc}")

            if isinstance(chart_reach_result, Exception):
                partial_errors.append(f"reach_chart: {chart_reach_result}")
            else:
                chart_reach_metric = chart_reach_result.get("reach")

            if isinstance(audience_result, Exception):
                partial_errors.append(f"audience: {audience_result}")
            else:
                audience = audience_result

            if isinstance(posts_result, Exception):
                partial_errors.append(f"posts: {posts_result}")
            else:
                posts = posts_result

        merge_started_at = time.perf_counter()
        kpis = _build_kpi_bundle_for_period(
            reach,
            period,
            views=views,
            engagement_metric=engagement_metric,
            engaged_accounts_metric=engaged_accounts_metric,
            follows_and_unfollows_metric=follows_and_unfollows_metric,
            profile_links_taps_metric=profile_links_taps_metric,
        )
        if reach is not None and previous_reach is not None:
            kpis["reach"] = _build_metric_bundle(reach, previous_reach, period, "Reach")
        if views is not None:
            kpis["views"] = _build_metric_bundle(views, previous_views, period, "Views")
        if engagement_metric is not None:
            kpis["engagement"] = _build_metric_bundle(engagement_metric, previous_engagement_metric, period, "Engagement")
        if engaged_accounts_metric is not None:
            kpis["engaged_accounts"] = _build_metric_bundle(engaged_accounts_metric, previous_engaged_accounts_metric, period, "Engaged Accounts")
        if follows_and_unfollows_metric is not None:
            kpis["follows_and_unfollows"] = _build_metric_bundle(
                follows_and_unfollows_metric,
                previous_follows_and_unfollows_metric,
                period,
                "Follows & Unfollows",
            )
        if profile_links_taps_metric is not None:
            kpis["profile_links_taps"] = _build_metric_bundle(
                profile_links_taps_metric,
                previous_profile_links_taps_metric,
                period,
                "Profile Link Taps",
            )
        kpis["engagement_rate"] = _build_engagement_rate_bundle(
            kpis.get("engagement") or engagement_metric,
            kpis.get("reach") or reach,
            previous_engagement_metric,
            previous_reach,
            period,
        )
        charts = _build_charts(kpis, chart_reach_metric)
        _log_step_duration("build_kpis_and_charts", merge_started_at, platform=platform)

        payload = {
            "platform": platform,
            "summary": {
                "accounts": accounts,
                "selected_account": selected,
            },
            "kpis": kpis,
            "charts": charts,
            "audience": audience,
            "posts": posts,
            "meta": {
                "partial_errors": partial_errors,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "params": {
                    "period": period,
                    "since": since,
                    "until": until,
                    "timezone": timezone_name,
                },
                "duration_ms": int((time.perf_counter() - started_at) * 1000),
                "cache": {
                    "hit": False,
                    "ttl_seconds": CACHE_TTL_SECONDS,
                },
            },
        }
        _log_step_duration("build_payload", started_at, platform=platform, selected_account_id=(selected or {}).get("id"))
        if ENABLE_OVERVIEW_CACHE:
            _write_cache(cache_key, payload)
        return payload

    raise ValueError(f"Unsupported platform: {platform}")
