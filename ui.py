"""
ui.py — All terminal UI components for Velox.

Uses Rich for layout/styling and Questionary for interactive prompts.
Keep all rendering logic here so main.py stays clean.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import questionary
from questionary import Style as QStyle
from rich import box
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()

# ─── Questionary dark theme ───────────────────────────────────────────────────

Q_STYLE = QStyle(
    [
        ("qmark",        "fg:#e5c07b bold"),
        ("question",     "fg:#abb2bf bold"),
        ("answer",       "fg:#98c379 bold"),
        ("pointer",      "fg:#61afef bold"),
        ("highlighted",  "fg:#61afef bold"),
        ("selected",     "fg:#56b6c2"),
        ("separator",    "fg:#5c6370"),
        ("instruction",  "fg:#5c6370"),
        ("text",         "fg:#abb2bf"),
        ("disabled",     "fg:#5c6370 italic"),
    ]
)

# ─── ASCII logo ───────────────────────────────────────────────────────────────

LOGO = r"""
 ██╗   ██╗███████╗██╗      ██████╗ ██╗  ██╗
 ██║   ██║██╔════╝██║     ██╔═══██╗╚██╗██╔╝
 ██║   ██║█████╗  ██║     ██║   ██║ ╚███╔╝
 ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║ ██╔██╗
  ╚████╔╝ ███████╗███████╗╚██████╔╝██╔╝ ██╗
   ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
"""

SUBTITLE = "Telegram Member Scraper  •  by Ryzz"


def print_logo() -> None:
    """Render the ASCII logo and subtitle in a centred Rich panel."""
    logo_text = Text(LOGO, style="bold cyan", justify="center")
    sub_text  = Text(SUBTITLE, style="dim white", justify="center")

    panel = Panel(
        Align.center(logo_text + sub_text),
        border_style="cyan",
        padding=(0, 4),
        box=box.DOUBLE_EDGE,
    )
    console.print(panel)
    console.print()


# ─── Menus ────────────────────────────────────────────────────────────────────

MAIN_CHOICES = [
    "  Scrape group members",
    "  Export results",
    "  Settings",
    "  Exit",
]


def _run_prompt(prompt_obj):
    """Run a questionary prompt object in the current thread (sync helper)."""
    return prompt_obj.ask()


async def _ask_async(prompt_obj):
    """Run a questionary prompt in a thread executor to avoid event-loop conflicts."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, prompt_obj.ask)


async def main_menu() -> str:
    """
    Display the main menu and return the chosen option label.
    Returns one of the MAIN_CHOICES strings.
    """
    return await _ask_async(
        questionary.select(
            "What would you like to do?",
            choices=MAIN_CHOICES,
            style=Q_STYLE,
            use_indicator=True,
            qmark="›",
        )
    )


async def ask_group() -> str:
    """Prompt the user for a Telegram group username or link."""
    return await _ask_async(
        questionary.text(
            "Enter group username or t.me link:",
            style=Q_STYLE,
            qmark="›",
        )
    )


async def ask_filter() -> bool:
    """Ask whether to scrape active members only. Returns True = active only."""
    choice = await _ask_async(
        questionary.select(
            "Member filter:",
            choices=[
                "Active users only  (online / recently / last week)",
                "All members",
            ],
            style=Q_STYLE,
            qmark="›",
        )
    )
    return choice.startswith("Active")


async def ask_otp() -> str:
    """Prompt for a Telegram OTP code."""
    return await _ask_async(
        questionary.password(
            "Enter the Telegram verification code sent to your phone:",
            style=Q_STYLE,
            qmark="›",
        )
    )


async def ask_2fa_password() -> str:
    """Prompt for a Telegram two-step verification (2FA) password."""
    return await _ask_async(
        questionary.password(
            "Enter your two-step verification password:",
            style=Q_STYLE,
            qmark="›",
        )
    )


async def confirm(message: str) -> bool:
    """Generic yes/no prompt."""
    return await _ask_async(
        questionary.confirm(message, style=Q_STYLE, qmark="›")
    )


# ─── Progress bar ─────────────────────────────────────────────────────────────

def make_progress() -> Progress:
    """Return a configured Rich Progress object for scraping."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[bold cyan]Scraping[/bold cyan]"),
        BarColumn(bar_width=40, style="cyan", complete_style="green"),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


# ─── Results display ──────────────────────────────────────────────────────────

def display_results(members: list[dict]) -> None:
    """Render a Rich table showing the scraped member data."""
    if not members:
        print_warning("No members to display.")
        return

    table = Table(
        title=f"[bold cyan]Scraped Members[/bold cyan]  [dim]({len(members)} total)[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        show_lines=False,
        row_styles=["", "dim"],  # Alternating row styles
    )

    table.add_column("#",            style="dim",       width=5,  justify="right")
    table.add_column("Username",     style="green",     min_width=16)
    table.add_column("Display Name", style="white",     min_width=20)
    table.add_column("User ID",      style="yellow",    min_width=12)
    table.add_column("Last Seen",    style="cyan",      min_width=16)
    table.add_column("Phone",        style="magenta",   min_width=14)

    for i, m in enumerate(members, start=1):
        table.add_row(
            str(i),
            m.get("username") or "[dim]—[/dim]",
            m.get("display_name") or "[dim]—[/dim]",
            str(m.get("user_id", "")),
            m.get("last_seen", "Unknown"),
            m.get("phone") or "[dim]hidden[/dim]",
        )

    console.print()
    console.print(table)
    console.print()


# ─── Settings display ─────────────────────────────────────────────────────────

def display_settings(env: dict[str, str]) -> None:
    """Render a panel showing all current .env configuration values."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key",   style="cyan", min_width=28)
    table.add_column("Value", style="white")

    for key, value in env.items():
        table.add_row(key, value)

    panel = Panel(
        table,
        title="[bold cyan]Current Configuration[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


async def settings_menu() -> str:
    """Settings sub-menu. Returns the chosen action label."""
    return await _ask_async(
        questionary.select(
            "Settings:",
            choices=[
                "Change delay between requests",
                "Change max members",
                "Show current config",
                "← Back to main menu",
            ],
            style=Q_STYLE,
            qmark="›",
        )
    )


async def ask_new_delay() -> str:
    """Prompt for a new delay value."""
    return await _ask_async(
        questionary.text(
            "New delay in seconds (e.g. 1.5):",
            style=Q_STYLE,
            qmark="›",
            validate=lambda v: v.replace(".", "", 1).isdigit() or "Please enter a number",
        )
    )


async def ask_new_max() -> str:
    """Prompt for a new max-members value."""
    return await _ask_async(
        questionary.text(
            "New max members (e.g. 1000):",
            style=Q_STYLE,
            qmark="›",
            validate=lambda v: v.isdigit() or "Please enter a whole number",
        )
    )


# ─── Notification helpers ─────────────────────────────────────────────────────

def print_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green]  {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow]  {message}")


def print_error(message: str) -> None:
    console.print(f"[bold red]✗[/bold red]  {message}")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]ℹ[/bold cyan]  {message}")


def print_flood_wait(seconds: int) -> None:
    console.print(
        f"[bold yellow]⏳  FloodWait:[/bold yellow] Telegram asked us to wait "
        f"[bold]{seconds}s[/bold] — retrying automatically…"
    )


def section_rule(title: str = "") -> None:
    """Print a horizontal divider with an optional centred title."""
    console.rule(f"[dim]{title}[/dim]" if title else "", style="cyan dim")
    console.print()
