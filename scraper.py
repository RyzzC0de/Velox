"""
scraper.py — Telegram scraping logic for Velox.

Wraps Telethon to:
  - Connect and authenticate the user session
  - Fetch group participants with rate-limiting
  - Handle FloodWaitError automatically
  - Yield member dicts that the rest of the app can consume
"""

import asyncio
import re

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChatAdminRequiredError,
    ChannelPrivateError,
    SessionPasswordNeededError,
    UserAlreadyParticipantError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
)
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import (
    UserStatusOnline,
    UserStatusRecently,
    UserStatusLastWeek,
    UserStatusLastMonth,
    UserStatusOffline,
)

import utils

# Session file is stored next to the script so it persists between runs.
SESSION_NAME = str(utils.PROJECT_ROOT / "velox_session")


def _build_client() -> TelegramClient:
    """Instantiate a Telethon client using credentials from .env."""
    return TelegramClient(
        SESSION_NAME,
        utils.get_api_id(),
        utils.get_api_hash(),
    )


def _format_last_seen(status) -> str:
    """Convert a Telethon UserStatus object into a human-readable string."""
    if isinstance(status, UserStatusOnline):
        return "Online"
    if isinstance(status, UserStatusRecently):
        return "Recently"
    if isinstance(status, UserStatusLastWeek):
        return "Last week"
    if isinstance(status, UserStatusLastMonth):
        return "Last month"
    if isinstance(status, UserStatusOffline):
        # was_online is a naive UTC datetime
        dt = status.was_online
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    return "Unknown"


def _is_active(status) -> bool:
    """Return True if the user was seen within the last week."""
    return isinstance(status, (UserStatusOnline, UserStatusRecently, UserStatusLastWeek))


def _invite_hash(group: str) -> str | None:
    """Extract the invite hash from a t.me/+ link, or return None."""
    m = re.search(r"t\.me/\+([A-Za-z0-9_-]+)", group)
    return m.group(1) if m else None


async def scrape_members(
    group: str,
    active_only: bool = False,
    progress_callback=None,
):
    """
    Async generator that yields one member dict per participant.

    Args:
        group:             Bare username (no @) of the target group/channel.
        active_only:       When True, skip members with no recent activity.
        progress_callback: Optional async callable(fetched: int, total: int)
                           invoked after every batch.

    Yields:
        {
            "user_id":      int,
            "username":     str,
            "display_name": str,
            "last_seen":    str,
            "phone":        str,
        }

    Raises:
        ChannelPrivateError, ChatAdminRequiredError, UsernameNotOccupiedError,
        UsernameInvalidError — callers should handle these for clean UX.
    """
    delay     = utils.get_delay()
    max_count = utils.get_max_members()
    client    = _build_client()

    await client.connect()

    # Ensure the session is authorised; send OTP if needed.
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError("NOT_AUTHORIZED")

    # ── Resolve entity ────────────────────────────────────────────────────
    # For private invite links (t.me/+hash):
    #   1. Try ImportChatInviteRequest — returns an Updates object whose
    #      .chats[0] is the resolved Chat/Channel.
    #   2. If already a member, UserAlreadyParticipantError is raised.
    #      In that case search dialogs for a chat whose invite link matches,
    #      or fall back to iterating dialogs to find it by title/id.
    invite_hash = _invite_hash(group)
    try:
        if invite_hash:
            try:
                updates = await client(ImportChatInviteRequest(invite_hash))
                entity = updates.chats[0]
            except UserAlreadyParticipantError:
                # Already a member — Telethon populates its entity cache when
                # ImportChatInviteRequest raises, so get_entity works now.
                entity = await client.get_entity(f"https://t.me/+{invite_hash}")
        else:
            entity = await client.get_entity(group)
    except (UsernameNotOccupiedError, UsernameInvalidError):
        await client.disconnect()
        raise

    # ── Get total member count for progress reporting ─────────────────────
    try:
        result = await client.get_participants(entity, limit=1)
        total = result.total
    except Exception:
        total = 0

    # ── Stream participants via iter_participants ──────────────────────────
    # Use limit=None so Telethon fetches all pages; we stop manually at
    # max_count after applying filters.  This ensures active_only filtering
    # doesn't silently cut the run short before reaching max_count.
    fetched = 0

    try:
        async for user in client.iter_participants(entity, limit=None):
            if user.bot:
                continue
            if active_only and not _is_active(user.status):
                continue

            yield {
                "user_id":      user.id,
                "username":     user.username or "",
                "display_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
                "last_seen":    _format_last_seen(user.status),
                "phone":        user.phone or "",
            }

            fetched += 1

            if fetched >= max_count:
                break

            if progress_callback and fetched % 50 == 0:
                await progress_callback(fetched, total)

            await asyncio.sleep(delay)

    except FloodWaitError as e:
        wait = e.seconds + 2
        if progress_callback:
            await progress_callback(fetched, total, flood_wait=wait)
        await asyncio.sleep(wait)
        # FloodWait mid-stream means we stop here; the caller can retry.

    if progress_callback:
        await progress_callback(fetched, max(total, fetched))

    await client.disconnect()


async def ensure_authorized(otp_callback, password_callback=None) -> bool:
    """
    Connect and, if not yet authorised, send an OTP and ask the user for it.
    If the account has 2FA enabled, prompts for the password via password_callback.

    Args:
        otp_callback:      async callable() → str  (prompts the user for the OTP code)
        password_callback: async callable() → str  (prompts the user for the 2FA password)

    Returns:
        True if the session is now authorised.
    """
    client = _build_client()
    await client.connect()

    if await client.is_user_authorized():
        await client.disconnect()
        return True

    await client.send_code_request(utils.get_phone())
    code = await otp_callback()
    try:
        await client.sign_in(utils.get_phone(), code)
    except SessionPasswordNeededError:
        if password_callback is None:
            await client.disconnect()
            raise RuntimeError("2FA is enabled but no password prompt was provided.")
        password = await password_callback()
        try:
            await client.sign_in(password=password)
        except Exception:
            await client.disconnect()
            raise
    except Exception:
        await client.disconnect()
        raise

    await client.disconnect()
    return True
