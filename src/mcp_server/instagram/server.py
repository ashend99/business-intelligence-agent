"""Instagram Analytics sub-server.

Defines the FastMCP instance and all Instagram tools. Mounted into the
top-level server (src/mcp_server/server.py) under the 'instagram' namespace.
Tools are thin wrappers around mcp_server.instagram.analytics functions.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from fastmcp import FastMCP

from mcp_server.instagram.analytics import (
    _get_insights_by_metric_names,
    get_accounts,
    get_all_posts_by_account_id,
    get_audience_demographics_by_account_id,
    get_engagement_breakdown_by_account_id,
    get_overview_metrics_by_account_id,
    get_posts_metrics_by_account_id,
    get_reach_timeseries_by_account_id,
    get_top_posts_by_account_id,
)
from mcp_server.instagram.client import GraphAPIError, close_client, init_client

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _parse_date(value: str | None) -> datetime | None:
    """Parse an ISO-8601 date string (YYYY-MM-DD) into a UTC-aware datetime."""
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Initialize the Instagram Graph API client on startup and close it on shutdown."""
    init_client()
    try:
        yield
    finally:
        await close_client()


mcp = FastMCP(
    name="instagram",
    instructions=(
        "Provides Instagram business account analytics via the Meta Graph API. "
        "Always call instagram_list_accounts first to resolve a valid account_id "
        "before calling any other Instagram tool. "
        "Dates must be ISO-8601 strings (YYYY-MM-DD)."
    ),
    lifespan=lifespan,
    version="1.0.0",
)


@mcp.tool
async def list_accounts() -> list[dict[str, Any]]:
    """List all Instagram business accounts linked to the configured access token.

    Paginates automatically and returns every account available to the token.
    Always call this first to get a valid account_id before calling any other tool.

    Returns:
        List of accounts, each with: account_id, username, name.
    """
    logger.info("list_accounts tool called")
    try:
        accounts = await get_accounts()
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")
    return [
        {
            "account_id": acc.id,
            "username": acc.username,
            "name": acc.name,
            # "profile_picture_url": acc.profile_picture_url,
            # "followers_count": acc.followers_count,
            # "follows_count": acc.follows_count,
            # "media_count": acc.media_count,
            # "page_id": acc.page_id,
            # "page_name": acc.page_name,
        }
        for acc in accounts
    ]


@mcp.tool
async def get_overview_metrics(
    account_id: str,
    since: str | None = None,
    until: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    """Get key performance metrics for an Instagram account over a date range.

    Fetches reach, views, total_interactions, accounts_engaged,
    follows_and_unfollows, and profile_links_taps in a single call.
    Use this for any question about reach, impressions, engagement totals,
    follower changes, or profile activity — do not call separate tools for these.

    Each metric in the response includes:
        - value: human-readable formatted total (e.g. "12.4K")
        - total_count: raw integer total
        - delta: percentage change vs the previous half of the window (e.g. "+8.3%")
        - spark: daily value array for charting
        - since / until: resolved date range
        - period: granularity used ("day", "week", etc.)

    Args:
        account_id: Instagram business account ID (from list_accounts).
        since: Start date as YYYY-MM-DD. Defaults to 28 days before until.
        until: End date as YYYY-MM-DD. Defaults to today.
        period: Aggregation granularity — "day", "week", "month".
                Defaults to "day" when omitted.
    """
    try:
        return await get_overview_metrics_by_account_id(
            account_id,
            since=_parse_date(since),
            until=_parse_date(until),
            period=period,
        )
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_reach_timeseries(
    account_id: str,
    since: str | None = None,
    until: str | None = None,
    period: str = "day",
) -> dict[str, Any]:
    """Get a daily reach time-series for charting over a date range.

    Returns a spark array of daily reach values suitable for rendering a
    line or bar chart. Unlike get_overview_metrics, this tool guarantees
    a populated spark array by automatically retrying with a time_series
    fallback if the initial API response returns no data points.

    Use this tool specifically when the user wants to visualise reach as
    a chart or trend over time. For a summary KPI value use get_overview_metrics.

    Args:
        account_id: Instagram business account ID (from list_accounts).
        since: Start date as YYYY-MM-DD. Defaults to 28 days before until.
        until: End date as YYYY-MM-DD. Defaults to today.
        period: Aggregation granularity — "day" or "week". Defaults to "day".

    Returns:
        reach: Metric summary containing:
            - spark: list of daily reach values for charting
            - value: human-readable total (e.g. "12.4K")
            - total_count: raw integer total
            - delta: percentage change vs previous half of the window
            - since / until: resolved date range
    """
    try:
        return await get_reach_timeseries_by_account_id(
            account_id,
            since=_parse_date(since),
            until=_parse_date(until),
            period=period,
        )
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_engagement_breakdown(
    account_id: str,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """Get engagement breakdown by type for an Instagram account over a date range.

    Returns total interactions split into individual components: likes, comments,
    saves, shares, reposts, replies, and other. Use this for donut or pie chart
    rendering, or when the user asks how engagement is distributed by type.

    Args:
        account_id: Instagram business account ID (from list_accounts).
        since: Start date as YYYY-MM-DD. Defaults to 28 days before until.
        until: End date as YYYY-MM-DD. Defaults to today.

    Returns:
        total_interactions: Total engagement count across all types.
        components_sum: Sum of all known breakdown components.
        breakdown: Dict of likes, comments, saves, shares, reposts, replies, other.
        since / until: Resolved date range.
    """
    try:
        return await get_engagement_breakdown_by_account_id(
            account_id,
            since=_parse_date(since),
            until=_parse_date(until),
        )
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_top_posts(
    account_id: str,
    since: str | None = None,
    until: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get top-performing Instagram posts ranked by engagement for a date range.

    Fetches recent media and ranks by engagement_total then reach. Use this
    when the user asks which posts performed best or wants a leaderboard view.
    To retrieve all posts without ranking use get_all_posts instead.

    Args:
        account_id: Instagram business account ID (from list_accounts).
        since: Start date as YYYY-MM-DD. Filters posts by creation date.
        until: End date as YYYY-MM-DD. Filters posts by creation date.
        limit: Maximum number of posts to return (default: 10, minimum: 1).

    Returns:
        List of posts each with: id, title, created_at, type (Image/Video/Reel/
        Carousel), reach, engagement_total, engagement_rate, thumbnail_url,
        media_url, permalink_url, reach_label, engagement_label.
    """
    try:
        return await get_top_posts_by_account_id(
            account_id,
            since=_parse_date(since),
            until=_parse_date(until),
            limit=limit,
        )
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_all_posts(account_id: str) -> list[dict[str, Any]]:
    """Get all Instagram posts (lifetime) for an account sorted by date descending.

    Paginates through the full media library and returns every post. Use this
    when the user wants a complete post history or a table/feed view.
    For ranking by performance use get_top_posts instead.

    Args:
        account_id: Instagram business account ID (from list_accounts).

    Returns:
        Full list of posts each with: id, title, created_at, type, reach,
        engagement_total, engagement_rate, thumbnail_url, media_url,
        permalink_url, reach_label, engagement_label.
    """
    try:
        return await get_all_posts_by_account_id(account_id)
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_posts_metrics(account_id: str) -> list[dict[str, Any]]:
    """Get detailed lifetime metrics for every Instagram post using media-level counts.

    Unlike get_all_posts which embeds insights, this tool uses native count
    fields (total_views_count, total_like_count, etc.) directly on each media
    object. Use this when the user wants a detailed per-post metrics table with
    individual counts for views, likes, comments, shares, reposts, and saves.

    Args:
        account_id: Instagram business account ID (from list_accounts).

    Returns:
        List of posts each with: id, title, created_at, type, view_count,
        like_count, comments_count, shares_count, reposts_count, saved_count,
        engagement_total, engagement_rate, thumbnail_url, media_url.
    """
    try:
        return await get_posts_metrics_by_account_id(account_id)
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_audience_demographics(account_id: str) -> dict[str, Any]:
    """Get lifetime engaged audience demographics for an Instagram account.

    Returns audience breakdown by age group, country, gender, and the
    cross-tabulation of gender by age group. Data reflects this month's
    engaged audience (users who interacted with content).

    Args:
        account_id: Instagram business account ID (from list_accounts).

    Returns:
        scope: "lifetime".
        age: Dict of age buckets (13-24, 25-34, 35-44, 45-54, 55+) → count.
        country: Top 9 countries by count plus "Other" → count.
        gender: Dict of Female / Male / Unknown → count.
        age_gender: Dict of age bucket → {Female, Male, Unknown} → count.
    """
    try:
        return await get_audience_demographics_by_account_id(account_id)
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")


@mcp.tool
async def get_custom_insights(
    account_id: str,
    metrics: list[str],
    since: str | None = None,
    until: str | None = None,
    period: str | None = None,
    metric_type: str | None = "total_value",
) -> dict[str, Any]:
    """Fetch any valid Instagram Graph API insight metrics by name.

    Power-user escape hatch for metrics not covered by other tools. Each metric
    in the response includes a summary with value, delta, spark, and date range.

    Common valid metric names: reach, views, total_interactions, accounts_engaged,
    follows_and_unfollows, profile_links_taps, likes, comments, saves, shares,
    reposts, replies, website_clicks, email_contacts, get_directions_clicks.

    Args:
        account_id: Instagram business account ID (from list_accounts).
        metrics: One or more Graph API metric names (e.g. ["reach", "views"]).
        since: Start date as YYYY-MM-DD. Defaults to 28 days before until.
        until: End date as YYYY-MM-DD. Defaults to today.
        period: Aggregation granularity — "day", "week", "month". Defaults to "day".
        metric_type: Graph API metric_type param — "total_value" (default)
                     or "time_series".
    """
    try:
        return await _get_insights_by_metric_names(
            account_id,
            tuple(metrics),
            since=_parse_date(since),
            until=_parse_date(until),
            period=period,
            metric_type=metric_type,
        )
    except GraphAPIError as e:
        raise RuntimeError(f"Instagram API error (code {e.code}): {e}")
