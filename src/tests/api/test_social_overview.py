"""Tests for GET /api/social/overview."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.social_overview import _compute_previous_window_bounds, build_social_overview
from mcp.instagram.analytics import get_overview_metrics_by_account_id


class TestSocialOverview:

    def test_computes_previous_window_with_same_length(self):
        previous = _compute_previous_window_bounds("2026-05-17", "2026-05-24")
        assert previous == ("2026-05-09", "2026-05-16")

    def test_rejects_unsupported_platform(self, client):
        resp = client.get("/api/social/overview", params={"platform": "tt"})
        assert resp.status_code == 400
        assert "Unsupported platform" in resp.json()["detail"]

    def test_rejects_instagram_window_over_90_days(self, client):
        with patch("api.main.settings.facebook_access_token", "token"):
            resp = client.get(
                "/api/social/overview",
                params={
                    "platform": "ig",
                    "period": "day",
                    "since": "2026-01-01",
                    "until": "2026-04-15",
                },
            )

        assert resp.status_code == 400
        assert "up to 90 days" in resp.json()["detail"]

    def test_returns_empty_payload_when_token_missing(self, client):
        with patch("api.main.settings.facebook_access_token", None):
            resp = client.get("/api/social/overview", params={"platform": "fb"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["platform"] == "fb"
        assert body["summary"]["accounts"] == []
        assert body["summary"]["selected_account"] is None

    def test_returns_aggregated_payload(self, client):
        payload = {
            "platform": "ig",
            "summary": {
                "accounts": [{"id": "1784", "name": "luster.ig"}],
                "selected_account": {"id": "1784", "name": "luster.ig"},
            },
            "kpis": {
                "reach": {"value": "10.4K", "delta": "8.2%", "spark": [10, 12, 14]},
                "engagement": None,
                "engaged_accounts": None,
                "engagement_rate": None,
                "followers": None,
                "video_views": None,
                "views": {"value": "9.8K", "delta": "7.5%", "spark": [9, 10, 12]},
            },
            "charts": {
                "reach_series": [10, 12, 14],
                "performance_overview": [],
            },
            "audience": {},
            "posts": [],
            "meta": {
                "partial_errors": [],
                "generated_at": "2026-05-24T00:00:00+00:00",
                "params": {
                    "period": "day",
                    "since": "2024-05-12",
                    "until": "2024-06-10",
                    "timezone": "UTC",
                },
                "duration_ms": 10,
                "cache": {"hit": False, "ttl_seconds": 120},
            },
        }

        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.build_social_overview",
            new=AsyncMock(return_value=payload),
        ) as overview_mock:
            resp = client.get(
                "/api/social/overview",
                params={
                    "platform": "ig",
                    "account_id": "1784",
                    "period": "day",
                    "since": "2024-05-12",
                    "until": "2024-06-10",
                    "timezone": "UTC",
                },
            )

        assert resp.status_code == 200
        assert resp.json() == payload
        overview_mock.assert_awaited_once_with(
            platform="ig",
            selected_account_id="1784",
            since="2024-05-12",
            until="2024-06-10",
            period="day",
            timezone_name="UTC",
            force_refresh=False,
        )


@pytest.mark.asyncio
async def test_build_social_overview_uses_previous_window_for_reach_comparison():
    current_metrics = {
        "reach": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "reach",
            "value": "11.2K",
            "total_count": 11220,
            "delta": "0.0%",
            "spark": [1250, 980, 1450, 2100, 1680, 890, 1320, 1550],
            "current_total": 11220,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-17",
            "until": "2026-05-24",
        },
        "views": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "views",
            "value": "8.1K",
            "total_count": 8120,
            "delta": "0.0%",
            "spark": [850, 920, 1100, 980, 1050, 1120, 960, 1140],
            "current_total": 8120,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-17",
            "until": "2026-05-24",
        },
        "total_interactions": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "total_interactions",
            "value": "2.3K",
            "total_count": 2320,
            "delta": "0.0%",
            "spark": [240, 280, 310, 300, 270, 300, 290, 330],
            "current_total": 2320,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-17",
            "until": "2026-05-24",
        },
        "accounts_engaged": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "accounts_engaged",
            "value": "1.1K",
            "total_count": 1120,
            "delta": "0.0%",
            "spark": [130, 140, 150, 130, 120, 140, 145, 165],
            "current_total": 1120,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-17",
            "until": "2026-05-24",
        },
    }
    previous_metrics = {
        "reach": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "reach",
            "value": "8.4K",
            "total_count": 8420,
            "delta": "0.0%",
            "spark": [850, 920, 1100, 1450, 980, 1200, 870, 1050],
            "current_total": 8420,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-09",
            "until": "2026-05-16",
        },
        "views": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "views",
            "value": "6.7K",
            "total_count": 6740,
            "delta": "0.0%",
            "spark": [760, 800, 870, 910, 780, 860, 750, 910],
            "current_total": 6740,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-09",
            "until": "2026-05-16",
        },
        "total_interactions": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "total_interactions",
            "value": "1.8K",
            "total_count": 1840,
            "delta": "0.0%",
            "spark": [190, 210, 220, 240, 210, 250, 230, 290],
            "current_total": 1840,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-09",
            "until": "2026-05-16",
        },
        "accounts_engaged": {
            "account_id": "1784",
            "account_name": "luster.ig",
            "metric": "accounts_engaged",
            "value": "900",
            "total_count": 900,
            "delta": "0.0%",
            "spark": [100, 110, 120, 105, 95, 110, 115, 145],
            "current_total": 900,
            "previous_total": 0,
            "period": "day",
            "since": "2026-05-09",
            "until": "2026-05-16",
        },
    }
    chart_metrics = {
        "reach": {
            "metric": "reach",
            "spark": [100, 120, 140, 160],
            "total_count": 520,
        },
        "views": {
            "metric": "views",
            "spark": [80, 90, 100, 110],
            "total_count": 380,
        },
    }
    posts_payload = [
        {
            "id": "m1",
            "title": "Top post",
            "created_at": "2026-05-22T11:00:00+00:00",
            "type": "Image",
            "reach": 4200,
            "engagement_total": 530,
            "engagement_rate": 12.62,
            "thumbnail_url": "https://example.com/p1.jpg",
            "permalink_url": "https://instagram.com/p/abc",
            "reach_label": "4.2K",
            "engagement_label": "530",
        }
    ]

    with patch("api.social_overview.get_accounts", new=AsyncMock(return_value=[SimpleNamespace(
        id="1784",
        name="luster.ig",
        username="luster.ig",
        profile_picture_url="",
        page_id="123",
        page_name="Luster",
    )])), patch(
        "api.social_overview.get_overview_metrics_by_account_id",
        new=AsyncMock(side_effect=[current_metrics, previous_metrics]),
    ) as reach_mock, patch(
        "api.social_overview.get_reach_timeseries_by_account_id",
        new=AsyncMock(return_value=chart_metrics),
    ), patch(
        "api.social_overview._fetch_audience_placeholder",
        new=AsyncMock(return_value={}),
    ), patch(
        "api.social_overview.get_top_posts_by_account_id",
        new=AsyncMock(return_value=posts_payload),
    ):
        payload = await build_social_overview(
            platform="ig",
            selected_account_id="1784",
            since="2026-05-17",
            until="2026-05-24",
            period="day",
            timezone_name="UTC",
            force_refresh=True,
        )

    assert reach_mock.await_count == 2
    first_kwargs = reach_mock.await_args_list[0].kwargs
    second_kwargs = reach_mock.await_args_list[1].kwargs
    assert first_kwargs["since"] == datetime(2026, 5, 17, tzinfo=timezone.utc)
    assert first_kwargs["until"] == datetime(2026, 5, 25, tzinfo=timezone.utc)
    assert second_kwargs["since"] == datetime(2026, 5, 9, tzinfo=timezone.utc)
    assert second_kwargs["until"] == datetime(2026, 5, 17, tzinfo=timezone.utc)

    reach = payload["kpis"]["reach"]
    assert reach["total_count"] == 11220
    assert reach["current_total"] == 11220
    assert reach["previous_total"] == 8420
    assert reach["change_value"] == "2,800"
    assert reach["delta"] == "33.3%"
    assert reach["comparison_label"] == "vs May 09 - May 16"
    assert reach["comparison_window"] == {"since": "2026-05-09", "until": "2026-05-16"}

    views = payload["kpis"]["views"]
    assert views["total_count"] == 8120
    assert views["current_total"] == 8120
    assert views["previous_total"] == 6740
    assert views["change_value"] == "1,380"
    assert views["delta"] == "20.5%"
    assert views["comparison_label"] == "vs May 09 - May 16"

    engagement = payload["kpis"]["engagement"]
    assert engagement["total_count"] == 2320
    assert engagement["previous_total"] == 1840
    assert engagement["comparison_label"] == "vs May 09 - May 16"

    engaged_accounts = payload["kpis"]["engaged_accounts"]
    assert engaged_accounts["total_count"] == 1120
    assert engaged_accounts["previous_total"] == 900
    assert engaged_accounts["comparison_label"] == "vs May 09 - May 16"

    engagement_rate = payload["kpis"]["engagement_rate"]
    assert engagement_rate["value"] == "20.68%"
    assert engagement_rate["previous_total"] == pytest.approx(21.8527, abs=0.0001)
    assert engagement_rate["change_value"] == "1.18 pp"
    assert engagement_rate["delta"] == "-5.4%"
    assert engagement_rate["comparison_label"] == "vs May 09 - May 16"

    performance_overview = payload["charts"]["performance_overview"]
    assert len(performance_overview) == 1
    assert performance_overview[0]["name"] == "Reach"
    assert performance_overview[0]["points"] == [100, 120, 140, 160]
    assert payload["posts"] == posts_payload


@pytest.mark.asyncio
async def test_get_overview_metrics_uses_single_graph_call():
    account = SimpleNamespace(
        id="1784",
        name="luster.ig",
        username="luster.ig",
        profile_picture_url="",
        page_id="123",
        page_name="Luster",
    )
    payload = {
        "data": [
            {"name": "reach", "title": "Reach", "description": "Reach metric", "total_value": {"value": 100}},
            {"name": "views", "title": "Views", "description": "Views metric", "total_value": {"value": 250}},
            {"name": "total_interactions", "title": "Interactions", "description": "Interactions metric", "total_value": {"value": 75}},
            {"name": "accounts_engaged", "title": "Engaged Accounts", "description": "Engaged accounts metric", "total_value": {"value": 60}},
        ]
    }

    client = AsyncMock()
    client.get = AsyncMock(return_value=payload)

    with patch("mcp.instagram.analytics.get_account_by_id", new=AsyncMock(return_value=account)), patch(
        "mcp.instagram.analytics.get_client",
        return_value=client,
    ):
        result = await get_overview_metrics_by_account_id(
            "1784",
            since=datetime(2026, 5, 17, tzinfo=timezone.utc),
            until=datetime(2026, 5, 24, tzinfo=timezone.utc),
            period="day",
        )

    client.get.assert_awaited_once()
    kwargs = client.get.await_args.kwargs
    assert kwargs["metric"] == "reach,views,total_interactions,accounts_engaged,follows_and_unfollows,profile_links_taps"
    assert result["reach"]["total_count"] == 100
    assert result["views"]["total_count"] == 250
    assert result["total_interactions"]["total_count"] == 75
    assert result["accounts_engaged"]["total_count"] == 60
