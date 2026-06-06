"""
Google OAuth2 flow for Calendar integration.

Flow:
  1. GET /api/calendar/accounts/{email}/connect  → returns {"auth_url": "..."}
  2. Frontend redirects user to auth_url (window.location.href = auth_url)
  3. Google redirects to GET /api/calendar/accounts/callback?code=...&state=...
  4. Backend exchanges code for tokens → saves via token_store
  5. Backend redirects to http://localhost:3000?calendar_connected=1&email=...
"""

import logging
import secrets
from datetime import datetime, timezone

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# In-memory CSRF state store: {state_token: {"email": ..., "flow": ...}}
# Stores the original Flow instance so its PKCE code_verifier survives until exchange.
_pending_states: dict[str, dict] = {}


def _make_flow(client_id: str, client_secret: str, redirect_uri: str) -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


def generate_auth_url(
    email: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> str:
    """Generate a Google OAuth2 authorization URL for the given account email."""
    state = secrets.token_urlsafe(32)
    flow = _make_flow(client_id, client_secret, redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",   # always return refresh_token
        login_hint=email,   # pre-fills the Google account picker
        state=state,
    )
    # Store the flow instance — its internal code_verifier must be reused at exchange time.
    _pending_states[state] = {"email": email, "flow": flow}
    return auth_url


def exchange_code(
    code: str,
    state: str,
    client_id: str = "",    # unused — kept for call-site compatibility
    client_secret: str = "",
    redirect_uri: str = "",
) -> tuple[str, str, str, datetime | None]:
    """
    Exchange the authorization code for tokens.
    Returns (email, access_token, refresh_token, token_expiry).
    Raises ValueError on invalid/expired state.
    """
    entry = _pending_states.pop(state, None)
    if entry is None:
        raise ValueError("Invalid or expired OAuth state token")

    email = entry["email"]
    flow = entry["flow"]   # reuse the original flow to preserve the code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials

    expiry = creds.expiry  # may be naive UTC datetime
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return email, creds.token, creds.refresh_token, expiry


def refresh_credentials(
    access_token: str,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> tuple[str, datetime | None]:
    """
    Refresh the access token using the stored refresh token.
    Returns (new_access_token, new_expiry).
    """
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(GoogleRequest())

    expiry = creds.expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return creds.token, expiry
