"""
Google Calendar API routes.

Endpoints:
    GET    /api/calendar/accounts                   — list configured accounts + connection status
    GET    /api/calendar/accounts/callback          — Google OAuth2 redirect handler
    GET    /api/calendar/accounts/{email}/connect   — generate OAuth auth URL
    DELETE /api/calendar/accounts/{email}           — disconnect an account

    GET    /api/calendar/events                     — fetch events (?start=&end=&emails=)
    POST   /api/calendar/events                     — create event
    PUT    /api/calendar/events/{event_id}          — update event
    DELETE /api/calendar/events/{event_id}          — delete event (?account_email=)
"""

import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from gcalendar import auth as cal_auth
from gcalendar import google_client as gcal
from gcalendar.token_store import delete_tokens, list_connected_emails, save_tokens
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar", tags=["calendar"])

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BUSINESS_CONFIG_PATH = _PROJECT_ROOT / "config" / "business_config.yaml"

FRONTEND_URL = "http://localhost:3000"


def _load_configured_accounts() -> list[dict]:
    with open(_BUSINESS_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("google_calendars", [])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateEventRequest(BaseModel):
    account_email: str
    title: str
    description: str = ""
    start: str          # ISO-8601 datetime or date string
    end: str            # ISO-8601 datetime or date string
    all_day: bool = False
    location: str = ""


class UpdateEventRequest(BaseModel):
    account_email: str
    title: str
    description: str = ""
    start: str
    end: str
    all_day: bool = False
    location: str = ""


def _build_event_body(req: CreateEventRequest | UpdateEventRequest) -> dict:
    if req.all_day:
        return {
            "summary": req.title,
            "description": req.description,
            "location": req.location,
            "start": {"date": req.start[:10]},
            "end": {"date": req.end[:10]},
        }
    return {
        "summary": req.title,
        "description": req.description,
        "location": req.location,
        "start": {"dateTime": req.start, "timeZone": "UTC"},
        "end": {"dateTime": req.end, "timeZone": "UTC"},
    }


# ---------------------------------------------------------------------------
# Account endpoints
# ---------------------------------------------------------------------------

@router.get("/accounts")
async def list_accounts():
    """Return all configured accounts with their connection status and assigned color."""
    configured = _load_configured_accounts()
    connected_emails = set(list_connected_emails())
    colors = gcal.ACCOUNT_COLORS

    return [
        {
            "name": acc["name"],
            "email": acc["email"],
            "connected": acc["email"] in connected_emails,
            "color": colors[i % len(colors)],
        }
        for i, acc in enumerate(configured)
    ]


@router.get("/accounts/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """Handle Google's OAuth2 redirect — exchange code for tokens and redirect to frontend."""
    try:
        email, access_token, refresh_token, expiry = cal_auth.exchange_code(
            code=code,
            state=state,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_redirect_uri,
        )
        configured = _load_configured_accounts()
        name = next((a["name"] for a in configured if a["email"] == email), email)

        save_tokens(
            email=email,
            name=name,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=expiry,
            encryption_key=settings.calendar_encryption_key,
        )
        redirect_url = (
            f"{FRONTEND_URL}?calendar_connected=1&email={urllib.parse.quote(email)}"
        )
        return RedirectResponse(url=redirect_url)

    except ValueError as e:
        logger.warning("OAuth callback error: %s", e)
        return RedirectResponse(url=f"{FRONTEND_URL}?calendar_error=1")
    except Exception as e:
        logger.error("OAuth callback unexpected error: %s", e)
        return RedirectResponse(url=f"{FRONTEND_URL}?calendar_error=1")


@router.get("/accounts/{email}/connect")
async def connect_account(email: str):
    """Generate a Google OAuth2 authorization URL for the given account email."""
    configured = _load_configured_accounts()
    if not any(a["email"] == email for a in configured):
        raise HTTPException(status_code=404, detail=f"Account {email} not in configured list")

    auth_url = cal_auth.generate_auth_url(
        email=email,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )
    return {"auth_url": auth_url}


@router.delete("/accounts/{email}")
async def disconnect_account(email: str):
    """Remove stored tokens for the given account."""
    removed = delete_tokens(email)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Account {email} is not connected")
    return {"disconnected": email}


# ---------------------------------------------------------------------------
# Event endpoints
# ---------------------------------------------------------------------------

@router.get("/events")
async def get_events(
    start: str | None = Query(None),
    end: str | None = Query(None),
    emails: str | None = Query(None),  # comma-separated; omit to fetch all connected
):
    """Fetch events across connected accounts within a date range."""
    now = datetime.now(timezone.utc)
    # Default window: current month start → +60 days
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    time_min = datetime.fromisoformat(start) if start else month_start
    time_max = datetime.fromisoformat(end) if end else month_start + timedelta(days=60)

    if time_min.tzinfo is None:
        time_min = time_min.replace(tzinfo=timezone.utc)
    if time_max.tzinfo is None:
        time_max = time_max.replace(tzinfo=timezone.utc)

    configured = _load_configured_accounts()
    connected_emails = set(list_connected_emails())
    target_emails = set(emails.split(",")) if emails else connected_emails
    colors = gcal.ACCOUNT_COLORS

    target_accounts = [
        {**acc, "color": colors[i % len(colors)]}
        for i, acc in enumerate(configured)
        if acc["email"] in target_emails and acc["email"] in connected_emails
    ]

    all_events: list[dict] = []
    for acc in target_accounts:
        try:
            events = gcal.get_events(
                email=acc["email"],
                account_name=acc["name"],
                color=acc["color"],
                time_min=time_min,
                time_max=time_max,
                settings=settings,
            )
            all_events.extend(events)
        except Exception as e:
            logger.error("Failed to fetch events for %s: %s", acc["email"], e, exc_info=True)

    all_events.sort(key=lambda e: e.get("start") or "")
    return all_events


@router.post("/events")
async def create_event(req: CreateEventRequest):
    """Create a new event on the specified account's primary calendar."""
    try:
        created = gcal.create_event(req.account_email, _build_event_body(req), settings)
        return {"id": created["id"], "html_link": created.get("htmlLink", "")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/events/{event_id}")
async def update_event(event_id: str, req: UpdateEventRequest):
    """Update an existing event on the specified account's calendar."""
    try:
        updated = gcal.update_event(req.account_email, event_id, _build_event_body(req), settings)
        return {"id": updated["id"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, account_email: str = Query(...)):
    """Delete an event from the specified account's primary calendar."""
    try:
        gcal.delete_event(account_email, event_id, settings)
        return {"deleted": event_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
