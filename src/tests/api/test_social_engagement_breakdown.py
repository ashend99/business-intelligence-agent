"""Tests for GET /api/social/engagement-breakdown."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch


class TestSocialEngagementBreakdown:

    def test_returns_empty_payload_when_token_missing(self, client):
        with patch("api.main.settings.facebook_access_token", None):
            resp = client.get(
                "/api/social/engagement-breakdown",
                params={"platform": "ig", "account_id": "1784"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["platform"] == "ig"
        assert body["account_id"] == "1784"
        assert body["total_interactions"] == 0

    def test_rejects_missing_account_for_instagram(self, client):
        with patch("api.main.settings.facebook_access_token", "token"):
            resp = client.get("/api/social/engagement-breakdown", params={"platform": "ig"})

        assert resp.status_code == 400
        assert "account_id is required" in resp.json()["detail"]

    def test_fetches_last_30_days_when_not_linked(self, client):
        payload = {
            "account_id": "1784",
            "metric": "engagement_breakdown",
            "total_interactions": 1000,
            "components_sum": 850,
            "breakdown": {
                "likes": 500,
                "comments": 120,
                "saves": 80,
                "shares": 70,
                "reposts": 40,
                "replies": 40,
                "other": 150,
            },
            "since": "2026-04-27",
            "until": "2026-05-26",
        }

        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.get_engagement_breakdown_by_account_id",
            new=AsyncMock(return_value=payload),
        ) as breakdown_mock:
            resp = client.get(
                "/api/social/engagement-breakdown",
                params={
                    "platform": "ig",
                    "account_id": "1784",
                    "link_to_window": "false",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["window_days"] == 30
        assert body["breakdown"]["other"] == 150
        assert body["total_interactions"] == 1000

        call_kwargs = breakdown_mock.await_args.kwargs
        assert call_kwargs["since"] is not None
        assert call_kwargs["until"] is not None

    def test_fetches_selected_window_when_linked(self, client):
        payload = {
            "account_id": "1784",
            "metric": "engagement_breakdown",
            "total_interactions": 120,
            "components_sum": 100,
            "breakdown": {
                "likes": 50,
                "comments": 20,
                "saves": 10,
                "shares": 8,
                "reposts": 6,
                "replies": 6,
                "other": 20,
            },
            "since": "2026-05-20",
            "until": "2026-05-26",
        }

        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.get_engagement_breakdown_by_account_id",
            new=AsyncMock(return_value=payload),
        ) as breakdown_mock:
            resp = client.get(
                "/api/social/engagement-breakdown",
                params={
                    "platform": "ig",
                    "account_id": "1784",
                    "since": "2026-05-20",
                    "until": "2026-05-26",
                    "link_to_window": "true",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["window_days"] == 7

        call_kwargs = breakdown_mock.await_args.kwargs
        assert call_kwargs["since"] == datetime(2026, 5, 20, tzinfo=timezone.utc)
        assert call_kwargs["until"] == datetime(2026, 5, 27, tzinfo=timezone.utc)

    def test_rejects_window_over_90_days_when_linked(self, client):
        with patch("api.main.settings.facebook_access_token", "token"):
            resp = client.get(
                "/api/social/engagement-breakdown",
                params={
                    "platform": "ig",
                    "account_id": "1784",
                    "since": "2026-01-01",
                    "until": "2026-05-10",
                    "link_to_window": "true",
                },
            )

        assert resp.status_code == 400
        assert "up to 90 days" in resp.json()["detail"]
