"""Low-level Facebook client backed by shared Graph API primitives.

Usage (singleton — recommended):
    from src.mcp.facebook.client import init_client, get_client

    # Once at startup (e.g. FastAPI lifespan / MCP server init):
    init_client("EAAxxxx...")

    # Everywhere else:
    client = get_client()
    data = await client.get("/me/accounts")

Usage (one-off / testing):
    async with FacebookGraphClient("EAAxxxx...") as client:
        data = await client.get("/me/accounts")
"""

from mcp.common.client import (
    GraphAPIError,
    GraphClient,
    close_singleton_client,
    get_singleton_client,
    init_singleton_client,
)

FACEBOOK_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

# Module-level singleton holder — reusable by shared helper functions.
_singleton: dict[str, GraphClient | None] = {"client": None}


class FacebookGraphClient(GraphClient):
    """Client for Facebook Graph API endpoints."""

    def __init__(self, access_token: str | None = None) -> None:
        super().__init__(
            access_token=access_token,
            base_url=FACEBOOK_GRAPH_API_BASE,
            token_env_var="FACEBOOK_ACCESS_TOKEN",
        )


# ── Singleton helpers ───────────────────────────────────────────────────────

def init_client(access_token: str | None = None) -> FacebookGraphClient:
    """Create (or replace) the module-level singleton client.

    Call this once at application startup — FastAPI lifespan, MCP server
    ``__main__``, or test fixtures.  All subsequent calls to ``get_client()``
    return the same instance, reusing its HTTP connection pool.

    Args:
        access_token: Token to use. Falls back to ``FACEBOOK_ACCESS_TOKEN`` env var.

    Returns:
        The newly created :class:`FacebookGraphClient`.
    """
    return init_singleton_client(_singleton, FacebookGraphClient, access_token)


def get_client() -> FacebookGraphClient:
    """Return the singleton client, initializing it lazily if needed.

    Lazy init reads ``FACEBOOK_ACCESS_TOKEN`` from the environment, so this
    works in scripts and tests without an explicit ``init_client()`` call.

    Returns:
        The shared :class:`FacebookGraphClient` instance.

    Raises:
        ValueError: If no token is available.
    """
    return get_singleton_client(_singleton, FacebookGraphClient)


async def close_client() -> None:
    """Close the singleton client and release its connection pool.

    Call this during application shutdown (FastAPI lifespan teardown /
    MCP server cleanup).
    """
    await close_singleton_client(_singleton)


__all__ = [
    "GraphAPIError",
    "FacebookGraphClient",
    "FACEBOOK_GRAPH_API_BASE",
    "init_client",
    "get_client",
    "close_client",
]
