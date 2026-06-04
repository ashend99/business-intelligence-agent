"""Social Analytics MCP Server — main entry point.

Mounts platform sub-servers under namespaced prefixes so all tools are
available through a single server connection.

Tool naming convention:
    instagram_<tool>   →  mcp_server.instagram.server
    facebook_<tool>    →  mcp_server.facebook.server  (coming soon)

Run:
    python -m mcp_server.server
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from fastmcp import FastMCP

from mcp_server.instagram.server import mcp as instagram_mcp
from config.settings import settings

_CONFIG_PATH = Path(os.getenv("PROJECT_DIR") or Path(__file__).resolve().parents[2]) / "src" / "mcp_server" / "config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


mcp = FastMCP(
    name="social-analytics",
    instructions=(
        "Provides social media analytics across platforms (Instagram, Facebook). "
        "Tools are namespaced by platform — e.g. instagram_list_accounts, "
        "facebook_list_pages. Always resolve a valid account_id via the "
        "list_accounts tool for the relevant platform before calling metric tools."
    ),
    version="1.0.0",
)

mcp.mount(instagram_mcp, namespace="instagram")


@mcp.tool
def get_current_date(timezone: str = "UTC") -> dict:
    """Get the current date and time in a given timezone.

    Use this before calling any analytics tool that needs a date range,
    so that 'today' is resolved correctly for the user's timezone rather
    than defaulting to UTC.

    Args:
        timezone: IANA timezone name (e.g. "Asia/Colombo", "America/New_York",
                  "Europe/London"). Defaults to "UTC".

    Returns:
        date: Current date as YYYY-MM-DD.
        datetime: Current date and time as ISO-8601 string.
        timezone: The timezone name that was used.
        utc_offset: UTC offset string (e.g. "+05:30").
    """
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Unknown timezone: '{timezone}'. Use an IANA timezone name e.g. 'Asia/Colombo'.")

    now = datetime.now(tz)
    offset = now.strftime("%z")
    utc_offset = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset

    return {
        "date": now.date().isoformat(),
        "datetime": now.isoformat(),
        "timezone": timezone,
        "utc_offset": utc_offset,
    }


@mcp.tool
def get_date_range(days_back: int, timezone: str = "UTC", until: str | None = None) -> dict:
    """Compute a since/until date range for analytics queries.

    Use this to translate user requests like 'last 7 days' or 'last 30 days'
    into the exact ISO-8601 since/until strings required by analytics tools.
    Dates are resolved in the user's local timezone, not UTC.

    Args:
        days_back: Number of days to look back from 'until' (e.g. 7, 28, 90).
        timezone: IANA timezone name (e.g. "Asia/Colombo", "America/New_York").
                  Defaults to "UTC".
        until: End date as YYYY-MM-DD. Defaults to today in the given timezone.

    Returns:
        since: Start date as YYYY-MM-DD (today minus days_back).
        until: End date as YYYY-MM-DD.
        days: The days_back value that was used.
        timezone: The timezone name that was used.
    """
    if days_back < 1:
        raise ValueError("days_back must be at least 1.")

    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Unknown timezone: '{timezone}'. Use an IANA timezone name e.g. 'Asia/Colombo'.")

    if until:
        until_date = datetime.fromisoformat(until).date()
    else:
        until_date = datetime.now(tz).date()

    since_date = until_date - timedelta(days=days_back)

    return {
        "since": since_date.isoformat(),
        "until": until_date.isoformat(),
        "days": days_back,
        "timezone": timezone,
    }


if __name__ == "__main__":
    cfg = _load_config().get("server", {})
    mcp.run(
        transport=cfg.get("transport", "http"),
        host=cfg.get("host", "0.0.0.0"),
        port=int(cfg.get("port", 8001)),
        log_level=cfg.get("log_level", "info"),
    )
