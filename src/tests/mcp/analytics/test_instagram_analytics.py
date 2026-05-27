"""Targeted tests for Instagram analytics helpers."""

import pytest

from mcp.instagram.analytics import _normalize_value, get_engagement_breakdown_by_account_id


def test_normalize_value_handles_nested_graph_payload():
    payload = {
        "value": {
            "value": 3,
        }
    }
    assert _normalize_value(payload) == 3


def test_normalize_value_handles_nested_total_key():
    payload = {
        "total_value": {
            "count": 7,
        }
    }
    assert _normalize_value(payload) == 7


def test_normalize_value_handles_list_wrapped_values():
    payload = [
        {"ignored": "x"},
        {"value": {"value": 5}},
    ]
    assert _normalize_value(payload) == 5


@pytest.mark.asyncio
async def test_engagement_breakdown_clamps_negative_component_values(monkeypatch):
    mocked = {
        "total_interactions": {"total_count": 1, "since": "2026-05-26", "until": "2026-05-26"},
        "likes": {"total_count": 0},
        "comments": {"total_count": 0},
        "saves": {"total_count": -1},
        "shares": {"total_count": 1},
        "reposts": {"total_count": 0},
        "replies": {"total_count": 0},
    }

    async def _fake_get_insights(*args, **kwargs):
        return mocked

    monkeypatch.setattr("mcp.instagram.analytics._get_insights_by_metric_names", _fake_get_insights)

    result = await get_engagement_breakdown_by_account_id("1784")

    assert result["total_interactions"] == 1
    assert result["breakdown"]["saves"] == 0
    assert result["breakdown"]["shares"] == 1
    assert result["breakdown"]["other"] == 0
