"""Configuration + lightweight runtime state + secret handling for ProSE.

Private, machine-local files live in the git-ignored ``instance/`` folder:
  * ``config.json``      -- settings (also edited via the dashboard)
  * ``.env``             -- the Gmail App Password (``PROSE_SMTP_PASSWORD``)
  * ``credentials.json`` / ``token.json`` -- Gmail OAuth client + token
  * ``.scan_state.json`` -- runtime status (last scan time, counts)
Generated spreadsheets live in the git-ignored ``data/`` folder.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Project root = parent of this package directory.
ROOT = Path(__file__).resolve().parent.parent
# Private, machine-local files (config, secrets, runtime state) live here.
INSTANCE = ROOT / "instance"
CONFIG_PATH = INSTANCE / "config.json"
STATE_PATH = INSTANCE / ".scan_state.json"
ENV_PATH = INSTANCE / ".env"

SECRET_KEY = "PROSE_SMTP_PASSWORD"

# Gmail API OAuth scope. gmail.compose authorizes sending mail.
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

# The 17 default keywords (from the original spec). Editable in the dashboard.
DEFAULT_KEYWORDS = [
    "Oracle",
    "Professional Services",
    "SharePoint",
    "Cloud",
    "Information Technology",
    "Database",
    "Web",
    "Analytics",
    "Artificial Intelligence",
    "SQL",
    "GIS",
    "Microsoft Fabric",
    "Data Engineering",
    "Cloud Data Migration",
    "Cloud Data Architecture - Data Warehouse, Data Lake",
    "AI Enablement",
    "Automation RPA",
]

DEFAULT_CONFIG = {
    "keywords": DEFAULT_KEYWORDS,
    # Schedule 1 (scan): mode is "daily" or "every_12h". For "daily" the scan
    # runs at hour:minute; for "every_12h" it runs at minute past every 12 hours
    # anchored on hour (hour and hour+12).
    "scan_schedule": {"mode": "daily", "hour": 6, "minute": 0},
    # Schedule 2 (email): any subset of weekdays + a time.
    "email_schedule": {
        "days": ["Mon"],  # one or more of Sun Mon Tue Wed Thu Fri Sat
        "hour": 8,
        "minute": 0,
    },
    "email": {
        # "gmail_api" = OAuth2 via the Gmail API (no App Password needed).
        # "smtp" = classic SMTP with an App Password (fallback).
        "method": "gmail_api",
        "sender": "",
        "recipients": [],
        "subject": "Scanned Professional Services - Weekly Update",
        # Gmail API OAuth client/token files (see README for setup).
        "credentials_file": "credentials.json",
        "token_file": "token.json",
        # SMTP fallback settings.
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "spreadsheet_path": "data/2026-2027 Scanned Professional Services.xlsx",
    "timezone": "Pacific/Honolulu",
}

DEFAULT_STATE = {
    "last_scan": None,        # ISO timestamp
    "last_scan_count": 0,     # solicitations found in last scan
    "last_scan_new": 0,       # newly-added rows in last scan
    "last_email": None,       # ISO timestamp
    "last_error": None,
}

WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
# APScheduler day_of_week tokens (it uses 3-letter lowercase).
_DOW_TOKEN = {d: d.lower() for d in WEEKDAYS}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into a copy of base (one level deep for nested dicts)."""
    out = json.loads(json.dumps(base))
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key].update(val)
        else:
            out[key] = val
    return out


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            user = json.load(fh)
        return _deep_merge(DEFAULT_CONFIG, user)
    # First run: materialise defaults.
    save_config(DEFAULT_CONFIG)
    return json.loads(json.dumps(DEFAULT_CONFIG))


def _atomic_json_write(path: Path, data: dict) -> None:
    """Write JSON via temp-file + replace so a concurrent reader (dashboard vs
    Task Scheduler-spawned scan/email process) never sees a half-written file."""
    INSTANCE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def save_config(cfg: dict) -> None:
    _atomic_json_write(CONFIG_PATH, cfg)


def load_state() -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            return _deep_merge(DEFAULT_STATE, json.load(fh))
    return json.loads(json.dumps(DEFAULT_STATE))


def save_state(state: dict) -> None:
    _atomic_json_write(STATE_PATH, state)


def update_state(**fields) -> dict:
    state = load_state()
    state.update(fields)
    save_state(state)
    return state


# --- .env / secret handling -------------------------------------------------

def load_env() -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no external dependency).

    Existing environment variables take precedence (not overwritten).
    """
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_smtp_password() -> str:
    return os.environ.get(SECRET_KEY, "")


def set_smtp_password(password: str) -> None:
    """Persist the App Password to .env and the live process environment."""
    INSTANCE.mkdir(parents=True, exist_ok=True)
    lines = []
    found = False
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if raw.strip().startswith(f"{SECRET_KEY}="):
                lines.append(f"{SECRET_KEY}={password}")
                found = True
            else:
                lines.append(raw)
    if not found:
        lines.append(f"{SECRET_KEY}={password}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[SECRET_KEY] = password


def spreadsheet_abspath(cfg: dict) -> Path:
    p = Path(cfg["spreadsheet_path"])
    return p if p.is_absolute() else ROOT / p


def credentials_path(cfg: dict) -> Path:
    p = Path(cfg["email"].get("credentials_file", "credentials.json"))
    return p if p.is_absolute() else INSTANCE / p.name


def token_path(cfg: dict) -> Path:
    p = Path(cfg["email"].get("token_file", "token.json"))
    return p if p.is_absolute() else INSTANCE / p.name


def dow_tokens(days: list[str]) -> str:
    """Convert ['Sun','Mon'] -> 'sun,mon' for APScheduler."""
    toks = [_DOW_TOKEN[d] for d in days if d in _DOW_TOKEN]
    return ",".join(toks) if toks else "mon"
