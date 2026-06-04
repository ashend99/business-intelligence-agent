"""Low-level HTTP clients for Instagram APIs.

For Instagram Insights and business account data, use ``InstagramGraphClient``
which targets the versioned Graph API host.

For Instagram Basic Display API, use ``InstagramBasicDisplayClient`` which
targets ``graph.instagram.com``.
"""

from mcp_server.common.client import (
    GraphAPIError,
    GraphClient,
    close_singleton_client,
    get_singleton_client,
    init_singleton_client,
)

INSTAGRAM_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
INSTAGRAM_BASIC_DISPLAY_API_BASE = "https://graph.instagram.com"

_singleton: dict[str, GraphClient | None] = {"client": None}


class InstagramGraphClient(GraphClient):
    """Client for Instagram Graph API (business/creator insights)."""

    def __init__(self, access_token: str | None = None) -> None:
        super().__init__(
            access_token=access_token,
            base_url=INSTAGRAM_GRAPH_API_BASE,
            token_env_var="FACEBOOK_ACCESS_TOKEN",
        )


class InstagramBasicDisplayClient(GraphClient):
    """Client for Instagram Basic Display API (consumer profile/media read)."""

    def __init__(self, access_token: str | None = None) -> None:
        super().__init__(
            access_token=access_token,
            base_url=INSTAGRAM_BASIC_DISPLAY_API_BASE,
            token_env_var="FACEBOOK_ACCESS_TOKEN",
        )


def init_client(access_token: str | None = None) -> InstagramGraphClient:
    """Create (or replace) the module-level singleton Instagram Graph client."""
    return init_singleton_client(_singleton, InstagramGraphClient, access_token)


def get_client() -> InstagramGraphClient:
    """Return the singleton Instagram Graph client, lazily initialized."""
    return get_singleton_client(_singleton, InstagramGraphClient)


async def close_client() -> None:
    """Close and clear the singleton Instagram Graph client."""
    await close_singleton_client(_singleton)


__all__ = [
    "GraphAPIError",
    "InstagramGraphClient",
    "InstagramBasicDisplayClient",
    "INSTAGRAM_GRAPH_API_BASE",
    "INSTAGRAM_BASIC_DISPLAY_API_BASE",
    "init_client",
    "get_client",
    "close_client",
]
