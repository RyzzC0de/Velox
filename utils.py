"""
utils.py — Shared helpers for Velox.

Handles .env loading, config management, and small utility functions
used across the rest of the codebase.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv, set_key

# Resolve paths relative to this file so the tool works from any CWD.
# When frozen by PyInstaller the executable lives at sys.executable; we want
# all user-facing files (.env, session, output/) to sit next to the .exe so
# users can edit them without hunting inside a temp directory.
import sys as _sys
if getattr(_sys, "frozen", False):
    PROJECT_ROOT = Path(_sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load .env on import so every module that imports utils gets the config.
load_dotenv(ENV_PATH)


# ─── Config accessors ─────────────────────────────────────────────────────────

def get_api_id() -> int | None:
    """Return TELEGRAM_API_ID as int, or None if unset."""
    raw = os.getenv("TELEGRAM_API_ID", "").strip()
    return int(raw) if raw.isdigit() else None


def get_api_hash() -> str:
    return os.getenv("TELEGRAM_API_HASH", "").strip()


def get_phone() -> str:
    return os.getenv("TELEGRAM_PHONE", "").strip()


def get_delay() -> float:
    """Return scraping delay in seconds (default 1.5)."""
    try:
        return float(os.getenv("DELAY_BETWEEN_REQUESTS", "1.5"))
    except ValueError:
        return 1.5


def get_max_members() -> int:
    """Return max member cap (default 500)."""
    try:
        return int(os.getenv("MAX_MEMBERS", "500"))
    except ValueError:
        return 500


def get_output_folder() -> Path:
    """Return output folder path, creating it if necessary."""
    folder = PROJECT_ROOT / os.getenv("OUTPUT_FOLDER", "output")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_env_snapshot() -> dict[str, str]:
    """Return a dict of all Velox-relevant env vars for display."""
    return {
        "TELEGRAM_API_ID":        os.getenv("TELEGRAM_API_ID", "(not set)"),
        "TELEGRAM_API_HASH":      _mask(os.getenv("TELEGRAM_API_HASH", "(not set)")),
        "TELEGRAM_PHONE":         os.getenv("TELEGRAM_PHONE", "(not set)"),
        "DELAY_BETWEEN_REQUESTS": os.getenv("DELAY_BETWEEN_REQUESTS", "1.5"),
        "MAX_MEMBERS":            os.getenv("MAX_MEMBERS", "500"),
        "OUTPUT_FOLDER":          os.getenv("OUTPUT_FOLDER", "output"),
    }


# ─── Config mutators ──────────────────────────────────────────────────────────

def update_env(key: str, value: str) -> None:
    """Persist a key=value pair to .env and update the running process."""
    set_key(str(ENV_PATH), key, value)
    os.environ[key] = value


# ─── Misc helpers ─────────────────────────────────────────────────────────────

def normalize_group(target: str) -> str:
    """
    Accept a raw group username or t.me link and return a value suitable for
    passing to Telethon's get_entity / iter_participants.

    Private invite links (t.me/+hash) are returned as the full URL so Telethon
    can resolve them via ImportChatInvite.  Public usernames are returned bare.

    Examples:
        "https://t.me/+uP5y6kZImNgyNTdk" → "https://t.me/+uP5y6kZImNgyNTdk"
        "https://t.me/somegroup"          → "somegroup"
        "@somegroup"                      → "somegroup"
        "somegroup"                       → "somegroup"
    """
    target = target.strip()
    # Invite link: t.me/+ — return the full URL for Telethon to handle
    if re.search(r"t\.me/\+", target):
        # Normalise to https:// form if the scheme is missing
        if not target.startswith("http"):
            target = "https://" + target.lstrip("/")
        return target
    # Public t.me URL — extract the bare username
    match = re.search(r"t\.me/([A-Za-z0-9_]+)", target)
    if match:
        return match.group(1)
    # Plain @username or bare username
    return target.lstrip("@")


def _mask(value: str, visible: int = 4) -> str:
    """Mask all but the last `visible` chars of a sensitive string."""
    if value in ("(not set)", ""):
        return value
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


def credentials_complete() -> bool:
    """Return True only if all three required credentials are set."""
    return bool(get_api_id() and get_api_hash() and get_phone())
