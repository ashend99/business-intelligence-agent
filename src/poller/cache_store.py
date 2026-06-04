"""File-based cache store for social metrics.

All workers share one JSON file. A FileLock guards every write; reads
retry until the lock is free, then fall back to an unlocked read after
the configured max-retry count.

Key schema
----------
Pre-warmed (semantic, date-independent — written by poller):
  overview|{platform}|{account_id}|30d_fixed
  analytics|{platform}|{account_id}|7d_default
  posts|{platform}|{account_id}|lifetime

Custom date-range (written on live fetch by route handlers):
  analytics|{platform}|{account_id}|{since}|{until}|{period}|{tz}|tpl:{n}|cmp:{b}
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

_POLLER_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def _load_config() -> dict:
    with open(_POLLER_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_cfg = _load_config()
_cache_cfg = _cfg.get("cache", {})

# Project root: src/poller -> src -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CACHE_FILE: Path = _PROJECT_ROOT / _cache_cfg.get("file_path", "cache/social_cache.json")
_LOCK_FILE: Path = _CACHE_FILE.with_suffix(".lock")

TTL_SECONDS: int = int(_cache_cfg.get("ttl_seconds", 1800))
_LOCK_TIMEOUT: float = float(_cache_cfg.get("lock_timeout_seconds", 10))
_READ_RETRY_INTERVAL_S: float = int(_cache_cfg.get("read_retry_interval_ms", 100)) / 1000.0
_READ_MAX_RETRIES: int = int(_cache_cfg.get("read_max_retries", 50))

_file_lock = FileLock(str(_LOCK_FILE), timeout=_LOCK_TIMEOUT)


class CacheHit(NamedTuple):
    payload: dict[str, Any]
    cached_at: str  # ISO-8601 UTC string


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_cache_dir() -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_raw() -> dict[str, Any]:
    if not _CACHE_FILE.exists():
        return {}
    try:
        with open(_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict[str, Any]) -> None:
    """Write atomically via a temp file + rename so readers never see a partial write."""
    _ensure_cache_dir()
    tmp = _CACHE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(_CACHE_FILE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read(key: str) -> CacheHit | None:
    """Return (payload, cached_at) if the key exists and is not expired, else None.

    Retries up to _READ_MAX_RETRIES times if the file is locked by a writer,
    then falls back to a best-effort unlocked read.
    """
    for _ in range(_READ_MAX_RETRIES):
        try:
            with _file_lock.acquire(timeout=0):   # non-blocking attempt
                data = _load_raw()
                entry = data.get(key)
                if entry is None or time.time() >= entry.get("expires_at", 0):
                    return None
                return CacheHit(payload=entry["payload"], cached_at=entry["cached_at"])
        except Timeout:
            time.sleep(_READ_RETRY_INTERVAL_S)

    # Max retries exhausted — read without the lock as a last resort
    logger.warning("cache_store: read lock timed out for key=%s, reading without lock", key)
    data = _load_raw()
    entry = data.get(key)
    if entry is None or time.time() >= entry.get("expires_at", 0):
        return None
    return CacheHit(payload=entry["payload"], cached_at=entry["cached_at"])


def write(key: str, payload: dict[str, Any]) -> None:
    """Write key→payload to the cache file.

    Acquires the write lock, evicts all expired entries in the same pass,
    then writes the updated dict atomically.
    """
    now = time.time()
    cached_at = datetime.now(timezone.utc).isoformat()
    try:
        with _file_lock:
            data = _load_raw()
            # Evict expired entries while we already hold the lock
            data = {k: v for k, v in data.items() if now < v.get("expires_at", 0)}
            data[key] = {
                "expires_at": now + TTL_SECONDS,
                "cached_at": cached_at,
                "payload": payload,
            }
            _save_raw(data)
    except Timeout:
        logger.error("cache_store: write lock timed out for key=%s — entry not written", key)


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------

def overview_key(platform: str, account_id: str) -> str:
    return f"overview|{platform}|{account_id}|30d_fixed"


def analytics_key(
    platform: str,
    account_id: str | None,
    since: str | None,
    until: str | None,
    period: str,
    timezone_name: str,
    top_posts_limit: int,
    compare_previous: bool,
) -> str:
    """Return a semantic key when no dates are given (maps to pre-warmed data),
    or a full date-range key for custom windows."""
    if not since and not until:
        return f"analytics|{platform}|{account_id or '-'}|7d_default"
    return (
        f"analytics|{platform}|{account_id or '-'}"
        f"|{since}|{until}|{period}|{timezone_name}"
        f"|tpl:{top_posts_limit}|cmp:{compare_previous}"
    )


def posts_key(platform: str, account_id: str | None, scope: str) -> str:
    return f"posts|{platform}|{account_id or '-'}|{scope}"


def accounts_key(platform: str) -> str:
    return f"accounts|{platform}"
