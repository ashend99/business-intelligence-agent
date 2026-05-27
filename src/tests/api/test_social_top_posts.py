"""Tests for GET /api/social/top-posts."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch


class TestSocialTopPosts:

    def test_returns_empty_payload_when_token_missing(self, client):
        with patch("api.main.settings.facebook_access_token", None):
            resp = client.get(
                "/api/social/top-posts",
                params={"platform": "ig", "account_id": "1784", "limit": 10},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["platform"] == "ig"
        assert body["account_id"] == "1784"
        assert body["posts"] == []

    def test_rejects_missing_account_for_instagram(self, client):
        with patch("api.main.settings.facebook_access_token", "token"):
            resp = client.get("/api/social/top-posts", params={"platform": "ig"})

        assert resp.status_code == 400
        assert "account_id is required" in resp.json()["detail"]

    def test_fetches_all_time_posts_when_not_linked(self, client):
        payload = [{"id": "m1", "engagement_total": 200}]

        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.get_top_posts_by_account_id",
            new=AsyncMock(return_value=payload),
        ) as posts_mock:
            resp = client.get(
                "/api/social/top-posts",
                params={
                    "platform": "ig",
                    "account_id": "1784",
                    "since": "2026-05-01",
                    "until": "2026-05-10",
                    "link_to_window": "false",
                    "limit": 10,
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["posts"] == payload
        posts_mock.assert_awaited_once_with(
            "1784",
            since=None,
            until=None,
            limit=10,
        )

    def test_fetches_windowed_posts_when_linked(self, client):
        payload = [{"id": "m1", "engagement_total": 200}]

        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.get_top_posts_by_account_id",
            new=AsyncMock(return_value=payload),
        ) as posts_mock:
            resp = client.get(
                "/api/social/top-posts",
                params={
                    "platform": "ig",
                    "account_id": "1784",
                    "since": "2026-05-01",
                    "until": "2026-05-10",
                    "link_to_window": "true",
                    "limit": 5,
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["posts"] == payload

        call_kwargs = posts_mock.await_args.kwargs
        assert call_kwargs["limit"] == 5
        assert call_kwargs["since"] == datetime(2026, 5, 1, tzinfo=timezone.utc)
        assert call_kwargs["until"] == datetime(2026, 5, 11, tzinfo=timezone.utc)

    def test_rejects_window_over_90_days_when_linked(self, client):
        with patch("api.main.settings.facebook_access_token", "token"):
            resp = client.get(
                "/api/social/top-posts",
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
