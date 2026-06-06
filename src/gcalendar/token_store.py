"""
Encrypted file-based store for Google OAuth tokens.

Unlike the social cache (social_cache.json), tokens have no TTL —
they persist until explicitly disconnected. The access_token and
refresh_token fields are Fernet-encrypted; all other metadata is plaintext.

File: cache/calendar_tokens.json
Structure:
    {
      "email@gmail.com": {
        "name": "LUSTER Cafe & Restaurant",
        "email": "email@gmail.com",
        "access_token": "<fernet-encrypted>",
        "refresh_token": "<fernet-encrypted>",
        "token_expiry": "2026-06-05T10:00:00+00:00",
        "connected_at": "2026-06-05T09:00:00+00:00"
      }
    }
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TOKEN_FILE: Path = _PROJECT_ROOT / "cache" / "calendar_tokens.json"
_LOCK_FILE: Path = _TOKEN_FILE.with_suffix(".lock")
_LOCK_TIMEOUT: float = 10.0

_file_lock = FileLock(str(_LOCK_FILE), timeout=_LOCK_TIMEOUT)


def _get_fernet(key: str) -> Fernet:
    return Fernet(key.encode() if isinstance(key, str) else key)


def _ensure_dir() -> None:
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_raw() -> dict:
    if not _TOKEN_FILE.exists():
        return {}
    try:
        with open(_TOKEN_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict) -> None:
    """Write atomically via temp file + rename so readers never see a partial write."""
    _ensure_dir()
    tmp = _TOKEN_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(_TOKEN_FILE)


def save_tokens(
    email: str,
    name: str,
    access_token: str,
    refresh_token: str,
    token_expiry: datetime | None,
    encryption_key: str,
) -> None:
    """Encrypt and persist OAuth tokens for an account."""
    f = _get_fernet(encryption_key)
    entry = {
        "name": name,
        "email": email,
        "access_token": f.encrypt(access_token.encode()).decode(),
        "refresh_token": f.encrypt(refresh_token.encode()).decode(),
        "token_expiry": token_expiry.isoformat() if token_expiry else None,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with _file_lock:
            data = _load_raw()
            data[email] = entry
            _save_raw(data)
    except Timeout:
        logger.error("token_store: write lock timed out for %s", email)
        raise


def load_tokens(email: str, encryption_key: str) -> dict | None:
    """Return decrypted token data for an account, or None if not connected."""
    data = _load_raw()
    entry = data.get(email)
    if not entry:
        return None
    f = _get_fernet(encryption_key)
    return {
        "name": entry["name"],
        "email": entry["email"],
        "access_token": f.decrypt(entry["access_token"].encode()).decode(),
        "refresh_token": f.decrypt(entry["refresh_token"].encode()).decode(),
        "token_expiry": entry.get("token_expiry"),
        "connected_at": entry.get("connected_at"),
    }


def update_access_token(
    email: str,
    access_token: str,
    token_expiry: datetime | None,
    encryption_key: str,
) -> None:
    """Update only the access_token + expiry after a token refresh."""
    f = _get_fernet(encryption_key)
    try:
        with _file_lock:
            data = _load_raw()
            if email not in data:
                return
            data[email]["access_token"] = f.encrypt(access_token.encode()).decode()
            data[email]["token_expiry"] = token_expiry.isoformat() if token_expiry else None
            _save_raw(data)
    except Timeout:
        logger.error("token_store: update lock timed out for %s", email)


def delete_tokens(email: str) -> bool:
    """Remove all tokens for an account. Returns True if the account existed."""
    try:
        with _file_lock:
            data = _load_raw()
            if email not in data:
                return False
            del data[email]
            _save_raw(data)
            return True
    except Timeout:
        logger.error("token_store: delete lock timed out for %s", email)
        return False


def list_connected_emails() -> list[str]:
    """Return emails of all currently connected accounts."""
    return list(_load_raw().keys())
