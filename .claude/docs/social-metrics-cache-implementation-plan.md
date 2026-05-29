# Social Metrics In-Memory Cache — Implementation Plan

## Overview

Enable and extend the existing in-memory cache in `src/api/social_overview.py` to cover all 3 social API routes with route-namespaced keys and a 15-minute TTL.

---

## Current State

- `_CACHE`, `_read_cache`, `_write_cache` already exist in `social_overview.py`
- `ENABLE_OVERVIEW_CACHE = False` — cache is disabled
- `CACHE_TTL_SECONDS = 120` — TTL is only 2 minutes
- Only the `/api/social/overview` route has cache wiring
- `/api/social/analytics` and `/api/social/posts` have no cache at all
- Single `_cache_key()` function used by overview only — no route namespace

---

## What Needs to Change

### 1. `src/api/social_overview.py`

**Enable the cache and set TTL**
```python
CACHE_TTL_SECONDS = 900   # 15 minutes
ENABLE_OVERVIEW_CACHE = True
```

**Replace** the existing `_cache_key()` with 3 route-specific key builders:

```python
def _overview_cache_key(platform, account_id, since, until, period, timezone):
    return (
        f"overview|{platform}|{account_id or '-'}"
        f"|{since or '-'}|{until or '-'}|{period}|{timezone}"
    )

def _analytics_cache_key(platform, account_id, since, until, period, timezone,
                          top_posts_limit, compare_previous):
    return (
        f"analytics|{platform}|{account_id or '-'}"
        f"|{since or '-'}|{until or '-'}|{period}|{timezone}"
        f"|tpl:{top_posts_limit}|cmp:{compare_previous}"
    )

def _posts_cache_key(platform, account_id, since, until, period, timezone,
                     scope, sort_by, limit, page):
    return (
        f"posts|{platform}|{account_id or '-'}"
        f"|{since or '-'}|{until or '-'}|{period}|{timezone}"
        f"|scope:{scope}|sort:{sort_by}|lim:{limit}|pg:{page}"
    )
```

**Update `build_social_overview()`**
- Replace `_cache_key(...)` call with `_overview_cache_key(...)`
- No other changes needed — read/write logic is already wired

---

### 2. `src/api/main.py`

**`social_analytics_tab()` route** — add cache read before the Meta API calls and cache write after building the response:

```python
cache_key = _analytics_cache_key(
    normalized_platform, account_id, since, until, period, timezone,
    top_posts_limit, compare_previous
)
if not refresh:
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached

# ... existing logic ...

_write_cache(cache_key, response_payload)
return response_payload
```

**`social_posts_tab()` route** — same pattern:

```python
cache_key = _posts_cache_key(
    normalized_platform, account_id, since, until, period, timezone,
    scope, sort_by, limit, page
)
if not refresh:
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached

# ... existing logic ...

_write_cache(cache_key, response_payload)
return response_payload
```

**Expose `_read_cache` and `_write_cache`** from `social_overview.py` — either import them in `main.py` or move them to a shared `cache.py` module.

**Add `refresh` query param** to analytics and posts routes (already exists on overview):
```python
refresh: bool = Query(default=False)
```

---

### 3. Cache invalidation (optional, future)

- Frontend already sends `refresh=true` on the overview call — extend this to analytics and posts tabs if needed
- Could add a `POST /api/social/cache/clear` endpoint for manual invalidation during development

---

## Key Schema Summary

| Route | Example Key |
|---|---|
| `/api/social/overview` | `overview\|ig\|17841400000000001\|2026-05-21\|2026-05-28\|day\|Asia/Colombo` |
| `/api/social/analytics` | `analytics\|ig\|17841400000000001\|2026-05-21\|2026-05-28\|day\|Asia/Colombo\|tpl:10\|cmp:true` |
| `/api/social/posts` | `posts\|ig\|17841400000000001\|2026-05-21\|2026-05-28\|day\|Asia/Colombo\|scope:lifetime\|sort:engagement_total\|lim:50\|pg:1` |

---

## Files to Touch

| File | Change |
|---|---|
| `src/api/social_overview.py` | Enable cache, raise TTL, replace `_cache_key` with 3 route-specific functions |
| `src/api/main.py` | Wire cache read/write into analytics and posts route handlers, add `refresh` param |

---

## Notes

- The `_CACHE` dict is process-local — cache is lost on server restart (acceptable for now)
- If uvicorn is run with `--workers > 1`, each worker has its own cache (no cross-worker sharing)
- If multi-worker support is needed later, replace `_CACHE` dict with Redis using the same key schema
- `ENABLE_OVERVIEW_CACHE` flag can stay as a kill-switch for disabling the cache without code changes
