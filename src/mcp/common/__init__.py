"""Shared MCP utilities and base clients."""

from .client import (
    GraphAPIError,
    GraphClient,
    close_singleton_client,
    get_singleton_client,
    init_singleton_client,
)

__all__ = [
    "GraphAPIError",
    "GraphClient",
    "init_singleton_client",
    "get_singleton_client",
    "close_singleton_client",
]
