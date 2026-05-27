"""Shared low-level Graph API primitives for Meta platform integrations."""

import os
from typing import Any, TypeVar

import httpx

DEFAULT_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
DEFAULT_TIMEOUT = 30  # seconds


class GraphAPIError(Exception):
    """Raised when the Graph API returns an error response."""

    def __init__(self, message: str, code: int | None = None, subcode: int | None = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode


class GraphClient:
    """Async HTTP client for Meta Graph APIs."""

    def __init__(
        self,
        access_token: str | None = None,
        base_url: str = DEFAULT_GRAPH_API_BASE,
        token_env_var: str = "FACEBOOK_ACCESS_TOKEN",
    ) -> None:
        token = access_token or os.environ.get(token_env_var)
        if not token:
            raise ValueError(
                "No access token provided. "
                f"Pass access_token= or set the {token_env_var} env var."
            )
        self._token = token
        self._base_url = base_url
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=DEFAULT_TIMEOUT,
        )

    async def get(self, path: str, **params: Any) -> dict:
        response = await self._http.get(
            path,
            params={"access_token": self._token, **params},
        )
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            raise

        if "error" in data:
            err = data["error"]
            raise GraphAPIError(
                err.get("message", "Unknown Graph API error"),
                code=err.get("code"),
                subcode=err.get("error_subcode"),
            )

        response.raise_for_status()
        return data

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "GraphClient":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()


TGraphClient = TypeVar("TGraphClient", bound=GraphClient)


def init_singleton_client(
    holder: dict[str, GraphClient | None],
    factory: type[TGraphClient],
    access_token: str | None = None,
) -> TGraphClient:
    """Create (or replace) a module-level singleton client via holder dict."""
    holder["client"] = factory(access_token)
    return holder["client"]


def get_singleton_client(
    holder: dict[str, GraphClient | None],
    factory: type[TGraphClient],
) -> TGraphClient:
    """Return singleton client, lazily creating it via factory if needed."""
    client = holder.get("client")
    if client is None:
        client = factory()
        holder["client"] = client
    return client


async def close_singleton_client(holder: dict[str, GraphClient | None]) -> None:
    """Close and clear a singleton client stored in holder dict."""
    client = holder.get("client")
    if client is not None:
        await client.close()
        holder["client"] = None
