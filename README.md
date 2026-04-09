<div align="center">

```
 ██╗   ██╗███████╗██╗      ██████╗ ██╗  ██╗
 ██║   ██║██╔════╝██║     ██╔═══██╗╚██╗██╔╝
 ██║   ██║█████╗  ██║     ██║   ██║ ╚███╔╝
 ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║ ██╔██╗
  ╚████╔╝ ███████╗███████╗╚██████╔╝██╔╝ ██╗
   ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
```

**Telegram Member Scraper** — fast, clean, terminal-native.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Telethon](https://img.shields.io/badge/Telethon-1.34+-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://github.com/LonamiWebs/Telethon)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Coded by [RyzzC0de](https://github.com/RyzzC0de)*

</div>

---

## Overview

Velox is a terminal tool for scraping Telegram group members using the official MTProto API via Telethon. It supports public and private groups, active-member filtering, 2FA authentication, and CSV export — all wrapped in a clean Rich + Questionary UI with arrow-key navigation.

---

## Features

| Feature | Details |
|---|---|
| **Public groups** | Username (`@group`, `t.me/group`, bare name) |
| **Private groups** | Full invite link (`t.me/+xxxx`) — joins automatically |
| **Active filter** | Online / recently seen / last week |
| **2FA support** | Prompts for cloud password when needed |
| **CSV export** | Timestamped files in configurable output folder |
| **Rate limiting** | Configurable delay + automatic FloodWait handling |
| **Session persistence** | Authenticates once, reuses session on next run |

---

## Requirements

- Python **3.11+**
- A Telegram account
- API credentials from [my.telegram.org/apps](https://my.telegram.org/apps)

---

## Installation

```bash
git clone https://github.com/RyzzC0de/Velox.git
cd Velox
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# Required
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_PHONE=+34600000000

# Optional — defaults shown
DELAY_BETWEEN_REQUESTS=1.5
MAX_MEMBERS=500
OUTPUT_FOLDER=output
```

| Variable | Required | Description |
|---|:---:|---|
| `TELEGRAM_API_ID` | ✅ | Integer ID from my.telegram.org |
| `TELEGRAM_API_HASH` | ✅ | Hash string from my.telegram.org |
| `TELEGRAM_PHONE` | ✅ | Phone in international format (`+34...`) |
| `DELAY_BETWEEN_REQUESTS` | — | Seconds between members (default `1.5`) |
| `MAX_MEMBERS` | — | Hard cap on members per run (default `500`) |
| `OUTPUT_FOLDER` | — | Directory for CSV exports (default `output/`) |

> **Note:** Never commit your `.env` file. It is listed in `.gitignore` by default.

---

## Usage

```bash
python main.py
```

Navigate with arrow keys, confirm with Enter:

```
› Scrape group members
  Export results
  Settings
  Exit
```

### Scraping a public group

```
Enter group username or t.me link: @durov
```

Accepted formats: `@group`, `t.me/group`, `https://t.me/group`, `group`

### Scraping a private group

```
Enter group username or t.me link: https://t.me/+uP5y6kZImNgyNTdk
```

If you are not already a member, Velox will join the group automatically using the invite link.

### First-time authentication

On first run, Telegram sends a verification code to your account. Enter it at the prompt. If two-step verification is enabled on your account, you will be asked for your cloud password as well.

The session is stored locally in `velox_session.session` — subsequent runs skip authentication entirely.

---

## Output

Exports are written to the configured output folder as timestamped CSVs:

```
output/velox_export_20240409_153012.csv
```

| Column | Description |
|---|---|
| `user_id` | Telegram user ID |
| `username` | @handle (blank if not set) |
| `display_name` | First and last name |
| `last_seen` | Last activity (Online / Recently / Last week / timestamp) |
| `phone` | Phone number (only visible if mutually shared) |

---

## Project Structure

```
Velox/
├── main.py          # Entry point — menu loop and flow orchestration
├── scraper.py       # Telethon client, auth, and member iteration
├── ui.py            # All terminal UI: menus, prompts, progress, tables
├── utils.py         # .env loading, config accessors, path helpers
├── requirements.txt
├── .env.example     # Credential template
└── .gitignore
```

---

## Disclaimer

This tool is intended for **educational and research purposes only**. You are solely responsible for how you use it. Ensure your usage complies with [Telegram's Terms of Service](https://telegram.org/tos) and applicable laws. The author provides no warranty and accepts no liability for misuse.

---

<div align="center">

*Coded with ❤️ by [RyzzC0de](https://github.com/RyzzC0de)*

</div>
