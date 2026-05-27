"""Tests for GET /api/social/facebook/reach."""

from unittest.mock import AsyncMock, patch


class TestFacebookReach:

    def test_returns_reach_payload(self, client):
        payload = {
            "page_name": "LUSTER Cafe",
            "metric": "page_impressions_unique",
            "value": "12.8K",
            "delta": "18.6%",
            "spark": [60, 62, 58, 65],
            "current_total": 12850,
            "previous_total": 10835,
        }

        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.get_reach",
            new=AsyncMock(return_value=payload),
        ):
            resp = client.get("/api/social/facebook/reach", params={"page_name": "LUSTER Cafe"})

        assert resp.status_code == 200
        assert resp.json() == payload

    def test_missing_page_returns_404(self, client):
        with patch("api.main.settings.facebook_access_token", "token"), patch(
            "api.main.get_reach",
            new=AsyncMock(side_effect=ValueError("Facebook page not found: Missing Page")),
        ):
            resp = client.get("/api/social/facebook/reach", params={"page_name": "Missing Page"})

        assert resp.status_code == 404
        assert "Missing Page" in resp.json()["detail"]

    def test_missing_token_returns_zero_payload(self, client):
        with patch("api.main.settings.facebook_access_token", None):
            resp = client.get("/api/social/facebook/reach", params={"page_name": "LUSTER Cafe"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["page_name"] == "LUSTER Cafe"
        assert body["value"] == "0"
        assert body["spark"] == []