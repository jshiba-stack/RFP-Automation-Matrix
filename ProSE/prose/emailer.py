"""Send the spreadsheet by email.

Two methods are supported:
  * "gmail_api" (default) -- OAuth2 via the Gmail API (gmail.compose scope). No
    App Password needed. This is the recommended path, especially when Google
    App Passwords are unavailable for the account.
  * "smtp" -- classic SMTP with a Gmail App Password (fallback).
"""

from __future__ import annotations

import base64
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from . import config


class EmailError(RuntimeError):
    pass


# --- shared message building -------------------------------------------------

def _build_message(cfg: dict, attachment: Path, body: str) -> EmailMessage:
    email_cfg = cfg["email"]
    sender = (email_cfg.get("sender") or "").strip()
    recipients = [r.strip() for r in email_cfg.get("recipients", []) if r.strip()]
    if not sender:
        raise EmailError("No sender address configured.")
    if not recipients:
        raise EmailError("No recipients configured.")

    msg = EmailMessage()
    msg["Subject"] = email_cfg.get("subject", "Scanned Professional Services")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    if attachment and Path(attachment).exists():
        data = Path(attachment).read_bytes()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=Path(attachment).name,
        )
    return msg


def _default_body() -> str:
    return (
        "Attached is the latest 2026-2027 Scanned Professional Services "
        "spreadsheet from the HiePRO/HANDS opportunity scanner.\n\n-- ProSE"
    )


# --- Gmail API (OAuth2) ------------------------------------------------------

def _load_gmail_credentials(cfg: dict, allow_interactive: bool = False):
    """Load (and refresh) Gmail API credentials. If allow_interactive, run the
    browser consent flow when no valid token exists."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_file = config.token_path(cfg)
    creds_file = config.credentials_path(cfg)
    scopes = config.GMAIL_SCOPES

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not allow_interactive:
        raise EmailError(
            "Gmail account not connected (no valid token). Click "
            "“Connect Gmail” in the dashboard, or run "
            "“python run.py auth-email”."
        )

    # Interactive consent flow.
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not creds_file.exists():
        raise EmailError(f"OAuth client file not found: {creds_file}")
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), scopes)
    creds = flow.run_local_server(port=0)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def gmail_connected(cfg: dict) -> bool:
    """True if a usable Gmail token exists (valid or refreshable)."""
    try:
        _load_gmail_credentials(cfg, allow_interactive=False)
        return True
    except Exception:  # noqa: BLE001
        return False


def authorize_gmail(cfg: dict | None = None) -> str:
    """Run the interactive OAuth consent flow and persist the token.

    Returns the authorized email address.
    """
    cfg = cfg or config.load_config()
    creds = _load_gmail_credentials(cfg, allow_interactive=True)
    return _gmail_address(creds)


def _gmail_address(creds) -> str:
    try:
        from googleapiclient.discovery import build

        gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = gmail.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:  # noqa: BLE001
        return ""


def _send_gmail_api(cfg: dict, msg: EmailMessage) -> None:
    from googleapiclient.discovery import build

    creds = _load_gmail_credentials(cfg, allow_interactive=False)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    gmail.users().messages().send(userId="me", body={"raw": raw}).execute()


# --- SMTP fallback -----------------------------------------------------------

def _send_smtp(cfg: dict, msg: EmailMessage) -> None:
    email_cfg = cfg["email"]
    password = config.get_smtp_password()
    if not password:
        raise EmailError(
            "No SMTP App Password set. Add it in the dashboard (or .env as "
            "PROSE_SMTP_PASSWORD), or switch the email method to Gmail API."
        )
    host = email_cfg.get("smtp_host", "smtp.gmail.com")
    port = int(email_cfg.get("smtp_port", 587))
    sender = email_cfg["sender"].strip()
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(sender, password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailError(
            "Gmail rejected the login. Check the sender address and App Password "
            "(2-Step Verification must be on)."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise EmailError(f"Failed to send email: {exc}") from exc


# --- public API --------------------------------------------------------------

def send_spreadsheet(cfg: dict, body: str | None = None) -> dict:
    """Send the configured spreadsheet to the recipient list.

    Returns {"recipients": [...], "attachment": str, "method": str}.
    """
    attachment = config.spreadsheet_abspath(cfg)
    if not attachment.exists():
        raise EmailError(f"Spreadsheet not found at {attachment}. Run a scan first.")

    msg = _build_message(cfg, attachment, body or _default_body())
    method = cfg["email"].get("method", "gmail_api")

    if method == "smtp":
        _send_smtp(cfg, msg)
    else:
        _send_gmail_api(cfg, msg)

    return {
        "recipients": [r.strip() for r in cfg["email"]["recipients"] if r.strip()],
        "attachment": str(attachment),
        "method": method,
    }
