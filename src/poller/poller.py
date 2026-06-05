"""Background social-metrics poller.

Runs one warm-up pass immediately on server start, then re-runs at the
configured interval. Each pass fetches all accounts for every platform
and writes pre-computed payloads into the shared file cache so that
route handlers can serve dashboards without live Meta API calls.

Account order: primary (index 0) first so the default dashboard view
is ready before the remaining accounts are processed.
"""

import sys
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from poller import cache_store
from api.social_overview import build_social_overview
from api.social_builders import build_analytics_payload, build_posts_payload
from mcp_server.instagram.analytics import get_accounts as _get_ig_accounts
from mcp_server.facebook.analytics import get_pages as _get_fb_pages
from config.settings import settings

logger = logging.getLogger(__name__)

_POLLER_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_config() -> dict:
    with open(_POLLER_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_cfg = _load_config()
_poller_cfg = _cfg.get("poller", {})
_defaults_cfg = _cfg.get("defaults", {})

_INTERVAL_SECONDS: int = int(_poller_cfg.get("interval_minutes", 30)) * 60
_STARTUP_WARM_UP: bool = bool(_poller_cfg.get("startup_warm_up", True))
_PLATFORMS: list[str] = _cfg.get("platforms", ["ig", "fb"])
_ANALYTICS_WINDOW_DAYS: int = int(_defaults_cfg.get("analytics_window_days", 7))
_OVERVIEW_WINDOW_DAYS: int = int(_defaults_cfg.get("overview_window_days", 30))
_TOP_POSTS_LIMIT: int = int(_defaults_cfg.get("top_posts_limit", 10))


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------

def _window(days: int) -> tuple[str, str]:
    """Return (since, until) ISO date strings for the last N days (inclusive)."""
    until = datetime.now(timezone.utc).date()
    since = until - timedelta(days=days - 1)
    return since.isoformat(), until.isoformat()


# ---------------------------------------------------------------------------
# Per-account warm-up
# ---------------------------------------------------------------------------

async def _warm_overview(platform: str, account_id: str) -> None:
    since, until = _window(_OVERVIEW_WINDOW_DAYS)
    try:
        payload = await build_social_overview(
            platform=platform,
            selected_account_id=account_id,
            since=since,
            until=until,
            period="day",
            timezone_name="UTC",
        )
        cache_store.write(cache_store.overview_key(platform, account_id), payload)
        logger.debug("poller warm overview ok platform=%s account=%s", platform, account_id)
    except Exception as exc:
        logger.error("poller warm overview FAILED platform=%s account=%s: %s", platform, account_id, exc)


async def _warm_analytics(platform: str, account_id: str) -> None:
    since, until = _window(_ANALYTICS_WINDOW_DAYS)

    analytics_cfg = settings.social_analytics if isinstance(settings.social_analytics, dict) else {}
    platform_rules = (
        analytics_cfg.get("platform_rules", {}).get(platform, {})
        if isinstance(analytics_cfg.get("platform_rules", {}), dict) else {}
    )
    include_sections: list = platform_rules.get("include_sections", []) if isinstance(platform_rules, dict) else []
    include_kpis: list = platform_rules.get("include_kpis", []) if isinstance(platform_rules, dict) else []

    try:
        payload = await build_analytics_payload(
            platform=platform,
            account_id=account_id,
            since=since,
            until=until,
            period="day",
            timezone_name="UTC",
            top_posts_limit=_TOP_POSTS_LIMIT,
            compare_previous=True,
            include_sections=include_sections,
            include_kpis=include_kpis,
        )
        # Write under the semantic key so route handlers with since=None/until=None hit it
        key = cache_store.analytics_key(platform, account_id, None, None, "day", "UTC", _TOP_POSTS_LIMIT, True)
        cache_store.write(key, payload)
        logger.debug("poller warm analytics ok platform=%s account=%s", platform, account_id)
    except Exception as exc:
        logger.error("poller warm analytics FAILED platform=%s account=%s: %s", platform, account_id, exc)


async def _warm_posts(platform: str, account_id: str) -> None:
    posts_cfg = settings.social_posts if isinstance(settings.social_posts, dict) else {}
    platform_rules = (
        posts_cfg.get("platform_rules", {}).get(platform, {})
        if isinstance(posts_cfg.get("platform_rules", {}), dict) else {}
    )
    include_sections: list = platform_rules.get("include_sections", []) if isinstance(platform_rules, dict) else []
    include_cards: list = platform_rules.get("include_cards", []) if isinstance(platform_rules, dict) else []

    try:
        payload = await build_posts_payload(
            platform=platform,
            account_id=account_id,
            scope="lifetime",
            since=None,
            until=None,
            sort_by="engagement_total",
            limit=50,
            page=1,
            include_sections=include_sections,
            include_cards=include_cards,
        )
        cache_store.write(cache_store.posts_key(platform, account_id, "lifetime"), payload)
        logger.debug("poller warm posts ok platform=%s account=%s", platform, account_id)
    except Exception as exc:
        logger.error("poller warm posts FAILED platform=%s account=%s: %s", platform, account_id, exc)


async def _warm_account(platform: str, account_id: str) -> None:
    """Pre-warm all 3 tabs for one account in parallel."""
    await asyncio.gather(
        _warm_overview(platform, account_id),
        _warm_analytics(platform, account_id),
        _warm_posts(platform, account_id),
        return_exceptions=True,
    )


# ---------------------------------------------------------------------------
# Full poll pass
# ---------------------------------------------------------------------------

async def _warm_accounts_list(platform: str, raw: list) -> None:
    """Cache the account list response for the given platform."""
    try:
        if platform == "ig":
            payload = {
                "accounts": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "username": a.username,
                        "picture_url": a.profile_picture_url,
                        "followers_count": a.followers_count,
                        "follows_count": a.follows_count,
                        "media_count": a.media_count,
                        "page_id": a.page_id,
                        "page_name": a.page_name,
                    }
                    for a in raw
                ]
            }
            cache_store.write(cache_store.accounts_key(platform), payload)
            logger.debug("poller warm accounts_list ok platform=%s count=%d", platform, len(raw))
    except Exception as exc:
        logger.error("poller warm accounts_list FAILED platform=%s: %s", platform, exc)


async def _poll() -> None:
    if not settings.facebook_access_token:
        logger.debug("poller: no facebook_access_token configured — skipping poll")
        return

    started_at = time.perf_counter()
    total_accounts = 0

    for platform in _PLATFORMS:
        try:
            if platform == "ig":
                raw = await _get_ig_accounts()
                account_ids = [a.id for a in raw]
            else:
                raw = await _get_fb_pages()
                account_ids = [p.id for p in raw]
        except Exception as exc:
            logger.error("poller: failed to fetch accounts platform=%s: %s", platform, exc)
            continue

        if not account_ids:
            logger.info("poller: no accounts found platform=%s", platform)
            continue

        # Cache the accounts list itself first so the frontend can load account selectors instantly
        await _warm_accounts_list(platform, raw)

        # Primary account first (dashboard default), then the rest
        for account_id in account_ids:
            await _warm_account(platform, account_id)
            total_accounts += 1

    duration_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "poller: poll complete accounts=%d duration_ms=%d next_in=%ds",
        total_accounts, duration_ms, _INTERVAL_SECONDS,
    )


# ---------------------------------------------------------------------------
# Entry point wired into FastAPI lifespan
# ---------------------------------------------------------------------------

async def start_poller() -> None:
    """Start the background poller. Runs until the process exits."""
    if _STARTUP_WARM_UP:
        logger.info("poller: running startup warm-up poll")
        await _poll()

    while True:
        await asyncio.sleep(_INTERVAL_SECONDS)
        logger.info("poller: scheduled interval reached, running poll")
        await _poll()


# ---------------------------------------------------------------------------
# Standalone warm-up — run once and exit
# Usage:  python -m src.poller.poller
#         (or as a Docker/k8s init step before starting the app server)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("poller: standalone warm-up starting")
    asyncio.run(_poll())
    logger.info("poller: standalone warm-up done — cache is ready")
