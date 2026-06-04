"""Tool-level tests for get_instagram_overview_metrics_tool.

Tests are isolated: they mock _get_insights_by_metric_names so the tool
logic (constraint enforcement, error handling) is verified independently
of the real Graph API.

Run a single test:
    pytest src/tests/mcp/server/test_overview_metrics_tool.py::test_period_week_is_corrected_to_day -v
"""

import os
import pytest
from unittest.mock import AsyncMock, patch

from agents.analytics.tools import get_instagram_overview_metrics_tool


# ---------------------------------------------------------------------------
# Minimal fake API payload
# ---------------------------------------------------------------------------

def _fake_metrics_result(account_id: str = "ig-123") -> dict:
    """Return a minimal valid overview metrics dict as the analytics function would."""
    return {
        "total_interactions": {
            "account_id": account_id,
            "account_name": "LUSTER Cafe",
            "metric": "total_interactions",
            "value": "1.2K",
            "total_count": 1200,
            "delta": "5.0%",
            "spark": [40, 42, 38, 45],
            "current_total": 630,
            "previous_total": 570,
            "period": "day",
            "since": "2026-04-01",
            "until": "2026-04-30",
        },
        "reach": {
            "account_id": account_id,
            "metric": "reach",
            "value": "8.5K",
            "total_count": 8500,
            "delta": "3.0%",
            "spark": [280, 290, 300, 310],
            "current_total": 4500,
            "previous_total": 4000,
            "period": "day",
            "since": "2026-04-01",
            "until": "2026-04-30",
        },
    }


# ---------------------------------------------------------------------------
# Unit tests (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_json_for_valid_call(monkeypatch):
    """A well-formed call returns a JSON string containing metric data."""
    import json

    monkeypatch.setattr("config.settings.settings.facebook_access_token", "fake-token")

    with patch(
        "mcp_server.instagram.analytics.get_overview_metrics_by_account_id",
        new=AsyncMock(return_value=_fake_metrics_result()),
    ), patch("agents.analytics.tools._reinit_http_clients"):
        result = get_instagram_overview_metrics_tool.invoke({
            "account_id": "ig-123",
            "since": "2026-04-01",
            "until": "2026-04-30",
            "period": "",
        })

    data = json.loads(result)
    assert "total_interactions" in data
    assert data["total_interactions"]["total_count"] == 1200


@pytest.mark.asyncio
async def test_period_week_is_corrected_to_day(monkeypatch):
    """Passing period='week' is silently corrected to 'day' (reach constraint).

    The tool must not raise; the analytics layer auto-corrects the period.
    """
    import json
    from mcp_server.instagram.analytics import _resolve_period_for_metrics, _load_config

    config = _load_config()
    metric_names = ("reach", "views", "total_interactions",
                    "accounts_engaged", "follows_and_unfollows", "profile_links_taps")

    resolved = _resolve_period_for_metrics(metric_names, "week", config)

    assert resolved == "day", (
        f"Expected period to be corrected to 'day', got '{resolved}'"
    )


@pytest.mark.asyncio
async def test_period_month_is_corrected_to_day(monkeypatch):
    """Passing period='month' is silently corrected to 'day'."""
    from mcp_server.instagram.analytics import _resolve_period_for_metrics, _load_config

    config = _load_config()
    metric_names = ("reach", "views", "total_interactions",
                    "accounts_engaged", "follows_and_unfollows", "profile_links_taps")

    resolved = _resolve_period_for_metrics(metric_names, "month", config)
    assert resolved == "day"


@pytest.mark.asyncio
async def test_empty_period_uses_default_day(monkeypatch):
    """Passing period='' or None uses the configured default ('day')."""
    from mcp_server.instagram.analytics import _resolve_period_for_metrics, _load_config

    config = _load_config()
    metric_names = ("reach",)

    assert _resolve_period_for_metrics(metric_names, None, config) == "day"
    assert _resolve_period_for_metrics(metric_names, "", config) == "day"


@pytest.mark.asyncio
async def test_since_beyond_lookback_is_clamped(monkeypatch):
    """since older than max_lookback_days is clamped to the earliest allowed date."""
    from datetime import datetime, timedelta, timezone
    from mcp_server.instagram.analytics import _clamp_since, _load_config

    config = _load_config()
    metric_names = ("reach",)

    # 3 years ago — clearly beyond 730-day limit
    old_since = datetime(2022, 1, 1, tzinfo=timezone.utc)
    until = datetime.now(timezone.utc)

    result = _clamp_since(old_since, until, metric_names, config)

    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    earliest_allowed = now - timedelta(days=730)

    assert result is not None
    assert result >= earliest_allowed
    assert result < until


@pytest.mark.asyncio
async def test_entire_range_beyond_lookback_falls_back_to_default_window(monkeypatch):
    """When both since AND until are older than 2 years, since is reset to None
    so _resolve_bounds falls back to the default rolling window."""
    from datetime import datetime, timezone
    from mcp_server.instagram.analytics import _clamp_since, _load_config

    config = _load_config()
    metric_names = ("reach",)

    # Both dates are in 2022 — entirely out of the 2-year window
    old_since = datetime(2022, 8, 1, tzinfo=timezone.utc)
    old_until = datetime(2022, 8, 31, tzinfo=timezone.utc)

    result = _clamp_since(old_since, old_until, metric_names, config)

    assert result is None, (
        "Expected None (fallback to default window) when whole range is beyond lookback"
    )


@pytest.mark.asyncio
async def test_no_token_returns_error_message(monkeypatch):
    """Returns a no-token error string when facebook_access_token is not set."""
    monkeypatch.setattr("config.settings.settings.facebook_access_token", None)

    result = get_instagram_overview_metrics_tool.invoke({
        "account_id": "ig-123",
        "since": "",
        "until": "",
        "period": "",
    })

    assert "not available" in result.lower() or "no access token" in result.lower()


# ---------------------------------------------------------------------------
# Integration test — hits the real Graph API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("FACEBOOK_ACCESS_TOKEN"),
    reason="FACEBOOK_ACCESS_TOKEN not set — skipping live API call",
)
async def test_integration_overview_metrics_live(monkeypatch):
    """Call the real Instagram Graph API for overview metrics.

    Requires FACEBOOK_ACCESS_TOKEN in environment and a valid account_id.
    Set LUSTER_TEST_IG_ACCOUNT_ID to the account to query, or it will skip.
    """
    import json
    from mcp_server.instagram.analytics import get_accounts
    from mcp_server.instagram.client import _singleton
    _singleton["client"] = None

    accounts = await get_accounts()
    if not accounts:
        pytest.skip("No Instagram accounts returned — cannot run overview metrics test")

    account_id = accounts[0].id

    # Request last 30 days with no period (auto-resolves to 'day')
    result = get_instagram_overview_metrics_tool.invoke({
        "account_id": account_id,
        "since": "",
        "until": "",
        "period": "",
    })

    data = json.loads(result)
    assert isinstance(data, dict)
    assert len(data) > 0

    # Every returned metric must have the expected shape
    for metric_name, metric_data in data.items():
        assert "value" in metric_data, f"{metric_name} missing 'value'"
        assert "total_count" in metric_data, f"{metric_name} missing 'total_count'"
        assert "period" in metric_data, f"{metric_name} missing 'period'"
        assert metric_data["period"] == "day", (
            f"{metric_name} returned period '{metric_data['period']}', expected 'day'"
        )
