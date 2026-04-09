"""
main.py — Entry point for Velox.

Wires together the UI (ui.py), scraping engine (scraper.py),
CSV export, and settings management.
"""

import asyncio
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Make sure the package root is importable when run directly ─────────────────
sys.path.insert(0, str(Path(__file__).parent))

from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
    ApiIdInvalidError,
)

import ui
import utils
from scraper import scrape_members, ensure_authorized


# ─── Scrape flow ──────────────────────────────────────────────────────────────

async def flow_scrape() -> list[dict]:
    """
    Guide the user through the full scrape workflow:
      1. Check credentials
      2. Ensure the Telegram session is authorised (OTP if needed)
      3. Ask for the target group and filter preference
      4. Stream members with a live progress bar
      5. Return the collected member list
    """
    ui.section_rule("Scrape Group Members")

    # ── Credentials check ──────────────────────────────────────────────────
    if not utils.credentials_complete():
        ui.print_error(
            "Telegram credentials are not set. "
            "Open [bold cyan]velox/.env[/bold cyan] and fill in "
            "TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE."
        )
        return []

    # ── Session auth (OTP + optional 2FA) ─────────────────────────────────
    async def otp_prompt() -> str:
        ui.print_info("A verification code has been sent to your Telegram account.")
        return await ui.ask_otp()

    async def password_prompt() -> str:
        ui.print_info("Two-step verification is enabled on this account.")
        return await ui.ask_2fa_password()

    try:
        await ensure_authorized(otp_prompt, password_prompt)
    except Exception as exc:
        ui.print_error(f"Authentication failed: {exc}")
        return []

    # ── Group + filter input ───────────────────────────────────────────────
    raw_group = await ui.ask_group()
    if not raw_group:
        return []

    group = utils.normalize_group(raw_group)
    active_only = await ui.ask_filter()

    ui.print_info(
        f"Scraping [bold cyan]@{group}[/bold cyan]  "
        f"{'(active users only)' if active_only else '(all members)'}  "
        f"— max [bold]{utils.get_max_members()}[/bold] members"
    )
    ui.console.print()

    # ── Live progress bar ──────────────────────────────────────────────────
    members: list[dict] = []
    progress = ui.make_progress()

    with progress:
        task_id = progress.add_task("scraping", total=None)

        async def on_progress(fetched: int, total: int, flood_wait: int = 0) -> None:
            if flood_wait:
                ui.print_flood_wait(flood_wait)
            progress.update(task_id, completed=fetched, total=total)

        try:
            async for member in scrape_members(group, active_only, on_progress):
                members.append(member)
        except ChannelPrivateError:
            ui.print_error(
                "That group is private. You must be a member to scrape it."
            )
            return []
        except ChatAdminRequiredError:
            ui.print_error(
                "Admin privileges are required to view members of this group."
            )
            return []
        except (UsernameNotOccupiedError, UsernameInvalidError):
            ui.print_error(
                f"Group [bold]@{group}[/bold] does not exist or the username is invalid."
            )
            return []
        except ApiIdInvalidError:
            ui.print_error(
                "Your TELEGRAM_API_ID / TELEGRAM_API_HASH pair is invalid. "
                "Re-check your [bold cyan].env[/bold cyan] file."
            )
            return []
        except RuntimeError as exc:
            ui.print_error(str(exc))
            return []
        except Exception as exc:
            ui.print_error(f"Unexpected error: {exc}")
            return []

        progress.update(task_id, completed=len(members), total=len(members))

    ui.print_success(f"Scraped [bold]{len(members)}[/bold] members.")
    return members


# ─── Export flow ──────────────────────────────────────────────────────────────

async def flow_export(members: list[dict]) -> None:
    """Write the current member list to a timestamped CSV in the output folder."""
    ui.section_rule("Export Results")

    if not members:
        ui.print_warning(
            "No data to export. Run [bold]Scrape group members[/bold] first."
        )
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = utils.get_output_folder() / f"velox_export_{timestamp}.csv"

    fieldnames = ["user_id", "username", "display_name", "last_seen", "phone"]

    with open(filename, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(members)

    ui.print_success(
        f"Exported [bold]{len(members)}[/bold] members to "
        f"[bold cyan]{filename}[/bold cyan]"
    )

    # Offer a preview of the table right after export.
    if await ui.confirm("Show results table?"):
        ui.display_results(members)


# ─── Settings flow ────────────────────────────────────────────────────────────

async def flow_settings() -> None:
    """Settings sub-menu: view / change delay, max members, or current config."""
    while True:
        ui.section_rule("Settings")
        choice = await ui.settings_menu()

        if choice is None or "Back" in choice:
            break

        elif "delay" in choice:
            new_val = await ui.ask_new_delay()
            if new_val:
                utils.update_env("DELAY_BETWEEN_REQUESTS", new_val)
                ui.print_success(f"Delay updated to [bold]{new_val}s[/bold].")

        elif "max members" in choice:
            new_val = await ui.ask_new_max()
            if new_val:
                utils.update_env("MAX_MEMBERS", new_val)
                ui.print_success(f"Max members updated to [bold]{new_val}[/bold].")

        elif "Show" in choice:
            ui.display_settings(utils.get_env_snapshot())


# ─── Main loop ────────────────────────────────────────────────────────────────

async def main() -> None:
    """Top-level event loop: draw logo, run main menu, dispatch flows."""
    # Clear the screen for a clean start.
    os.system("cls" if os.name == "nt" else "clear")
    ui.print_logo()

    # Holds the last-scraped member list so it survives across menu iterations.
    current_members: list[dict] = []

    while True:
        choice = await ui.main_menu()

        if choice is None or "Exit" in choice:
            ui.print_info("Goodbye.")
            break

        elif "Scrape" in choice:
            result = await flow_scrape()
            if result:
                current_members = result
                if await ui.confirm("View results now?"):
                    ui.display_results(current_members)

        elif "Export" in choice:
            await flow_export(current_members)

        elif "Settings" in choice:
            await flow_settings()

        ui.console.print()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ui.console.print("\n[dim]Interrupted — exiting Velox.[/dim]")
        sys.exit(0)
