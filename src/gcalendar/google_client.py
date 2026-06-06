"""
Google Calendar API wrapper.

All public functions accept the account email, load credentials from
token_store, auto-refresh the access token when expired, and persist
the refreshed token back to disk.
"""

import logging
from datetime import datetime, timezone

import httplib2
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gcalendar.auth import SCOPES
from gcalendar.token_store import load_tokens, update_access_token

logger = logging.getLogger(__name__)

# Assigned to accounts in order; cycles if more than 6 accounts are connected.
ACCOUNT_COLORS = ["#6C63FF", "#00C9A7", "#F5A623", "#FF6B6B", "#4A8CFF", "#9B59B6"]


def _get_service(email: str, settings):
    """Build an authenticated Google Calendar service for the given account."""
    token_data = load_tokens(email, settings.calendar_encryption_key)
    if not token_data:
        raise ValueError(f"Account {email} is not connected")

    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        expiry = creds.expiry
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        update_access_token(email, creds.token, expiry, settings.calendar_encryption_key)

    # Use a 15-second timeout so a blocked/offline account fails fast
    # instead of hanging the entire events request for 60+ seconds.
    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=15))
    return build("calendar", "v3", http=http, cache_discovery=False)


def _normalize_event(event: dict, account_email: str, account_name: str, color: str) -> dict:
    """Convert a Google Calendar event to the internal API format."""
    start = event.get("start", {})
    end = event.get("end", {})
    all_day = "date" in start

    return {
        "id": event["id"],
        "title": event.get("summary", "(No title)"),
        "description": event.get("description", ""),
        "start": start.get("date") if all_day else start.get("dateTime"),
        "end": end.get("date") if all_day else end.get("dateTime"),
        "all_day": all_day,
        "account_email": account_email,
        "account_name": account_name,
        "color": color,
        "location": event.get("location", ""),
        "html_link": event.get("htmlLink", ""),
    }


def get_events(
    email: str,
    account_name: str,
    color: str,
    time_min: datetime,
    time_max: datetime,
    settings,
) -> list[dict]:
    """Fetch events within [time_min, time_max] from the account's primary calendar."""
    try:
        service = _get_service(email, settings)
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=250,
            )
            .execute()
        )
        return [_normalize_event(e, email, account_name, color) for e in result.get("items", [])]
    except Exception:
        raise


def create_event(email: str, event_body: dict, settings) -> dict:
    """Create an event on the account's primary calendar."""
    try:
        service = _get_service(email, settings)
        return service.events().insert(calendarId="primary", body=event_body).execute()
    except HttpError as e:
        logger.error("create_event failed for %s: %s", email, e)
        raise


def update_event(email: str, event_id: str, event_body: dict, settings) -> dict:
    """Update an existing event on the account's primary calendar."""
    try:
        service = _get_service(email, settings)
        return (
            service.events()
            .update(calendarId="primary", eventId=event_id, body=event_body)
            .execute()
        )
    except HttpError as e:
        logger.error("update_event failed for %s/%s: %s", email, event_id, e)
        raise


def delete_event(email: str, event_id: str, settings) -> None:
    """Delete an event from the account's primary calendar."""
    try:
        service = _get_service(email, settings)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except HttpError as e:
        logger.error("delete_event failed for %s/%s: %s", email, event_id, e)
        raise
