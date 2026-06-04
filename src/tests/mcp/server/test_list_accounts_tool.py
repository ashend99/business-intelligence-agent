"""Integration tests for the Instagram MCP list_accounts tool.

These tests intentionally avoid mocks and hit the real Graph API.

Run this file:
    pytest src/tests/mcp/server/test_list_accounts_tool.py -v
"""

import os

import pytest

from mcp_server.instagram.client import _singleton, close_client
from mcp_server.instagram.server import list_accounts
from config.settings import settings


async def _reset_instagram_client_singleton() -> None:
    """Ensure each test starts with a fresh Graph client instance."""
    await close_client()
    _singleton["client"] = None


@pytest.mark.asyncio
async def test_list_accounts_live_returns_expected_shape():
    """With a real valid token, list_accounts returns account dictionaries."""
    await _reset_instagram_client_singleton()

    result = await list_accounts()

    assert isinstance(result, list)
    if not result:
        pytest.skip("Token returned no Instagram business accounts")

    expected_keys = {
        "account_id",
        "username",
        "name",
        "profile_picture_url",
        "followers_count",
        "follows_count",
        "media_count",
        "page_id",
        "page_name",
    }

    first = result[0]
    assert expected_keys.issubset(first.keys())
    assert isinstance(first["account_id"], str)
    assert isinstance(first["username"], str)
    assert isinstance(first["name"], str)
    assert isinstance(first["profile_picture_url"], str)
    assert isinstance(first["followers_count"], int)
    assert isinstance(first["follows_count"], int)
    assert isinstance(first["media_count"], int)
    assert isinstance(first["page_id"], str)
    assert isinstance(first["page_name"], str)


