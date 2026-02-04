# TradingEconomics News to Discord

Fetches latest news from [TradingEconomics](https://tradingeconomics.com) via their API, deduplicates by article ID, and sends notifications with **direct links** to each article to a Discord channel. Use the Discord app on your phone to get push notifications with links that open the TradingEconomics page.

TradingEconomics does not offer a public RSS feed; this project uses their [news API](https://docs.tradingeconomics.com/news/latest/) instead.

## Prerequisites

- Python 3.10+
- A Discord server/channel and a [webhook URL](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) for that channel

## Setup

1. Clone or copy this project and go into its directory:
   ```bash
   cd newsSummary
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy the example env file and set your Discord webhook:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - **`DISCORD_WEBHOOK_URL`** (required): Create a webhook in Discord: Server → Channel → Edit Channel → Integrations → Webhooks → New Webhook, then copy the webhook URL.
   - **`TRADING_ECONOMICS_API_KEY`** (optional): Leave unset to use `guest:guest` (limited access). For production, get a key at [TradingEconomics API](https://tradingeconomics.com/api/).

## Run

Use the venv Python (works on macOS where `python` may not be in PATH), or run `source .venv/bin/activate` first and then use `python`.

**One shot** (run once and exit):

```bash
.venv/bin/python run_news_notifier.py
```

**Loop** (run forever, check every 15 minutes by default):

```bash
.venv/bin/python run_news_notifier.py --loop
```

Custom interval (e.g. every 30 minutes):

```bash
.venv/bin/python run_news_notifier.py --loop --interval 1800
```

Or set `NOTIFIER_INTERVAL_SECONDS=1800` in `.env`. Intervals under 60 seconds are forced to 60 to respect API rate limits.

- First run: fetches the latest articles and sends all of them to Discord (then saves state).
- Later runs: only new articles since the last run are sent. Stop the loop with Ctrl+C.

State is stored in `state/seen_ids.json` (gitignored). The script keeps the last 1000 seen IDs to avoid file growth.

## Scheduling

Run the script periodically (e.g. every 15–30 minutes) so new articles are pushed to Discord. Your machine must be on and connected; Discord then delivers notifications to your phone.

### Cron (macOS / Linux)

```bash
# Every 15 minutes
*/15 * * * * cd /path/to/newsSummary && .venv/bin/python run_news_notifier.py
```

Replace `/path/to/newsSummary` with the absolute path to this project. Add the line with `crontab -e`.

### launchd (macOS)

An example plist is in `com.newsnotifier.plist.example`. Install it so the script runs every 15 minutes:

1. Copy the example and set the paths inside to your project and Python:
   ```bash
   cp com.newsnotifier.plist.example ~/Library/LaunchAgents/com.newsnotifier.plist
   # Edit the plist and replace /path/to/newsSummary and /path/to/python with your paths
   ```

2. Load and start:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.newsnotifier.plist
   ```

To stop: `launchctl unload ~/Library/LaunchAgents/com.newsnotifier.plist`.

## Running 24/7 (without your computer)

To have the notifier run around the clock without keeping your machine on, use one of these.

### Option A: GitHub Actions (recommended, free)

GitHub runs the script every 15 minutes in the cloud. No server or credit card.

1. **Push this repo to GitHub** (public or private).

2. **Add repository secrets** (repo → Settings → Secrets and variables → Actions → New repository secret):
   - `DISCORD_WEBHOOK_URL` — your Discord webhook URL (required).
   - `TRADING_ECONOMICS_API_KEY` — optional; leave out to use guest access.

3. **Push the workflow** (it lives in `.github/workflows/news-notifier.yml`). Once pushed, the schedule runs every 15 minutes.

4. **Optional:** Run it once by hand: Actions → "News Notifier" → Run workflow.

State (seen article IDs) is stored in GitHub’s cache between runs so you don’t get duplicate notifications. Public repos have unlimited Actions minutes; private repos get a free allowance that’s enough for a run every 15 minutes.

### Option B: PythonAnywhere (free tier)

[PythonAnywhere](https://www.pythonanywhere.com/) lets you run a scheduled task on their servers.

1. Sign up (free), then create a new project and upload this repo (or clone it).

2. In a Bash console, create a venv and install deps:  
   `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

3. Add a **Scheduled task** (Tasks tab): run  
   `venv/bin/python run_news_notifier.py`  
   and set the schedule (e.g. every 15 minutes). The free tier has limited cron frequency; check their docs.

4. Set env vars in the task or in a `.env` file in the project: `DISCORD_WEBHOOK_URL` and optionally `TRADING_ECONOMICS_API_KEY`.

State is stored in your project directory on their disk and persists between runs.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Yes | Discord webhook URL for the channel where notifications are sent |
| `TRADING_ECONOMICS_API_KEY` | No | TE API key; if unset, uses `guest:guest` (limited access) |
| `NOTIFIER_INTERVAL_SECONDS` | No | Loop interval in seconds when using `--loop` (default: 900) |

## Files

- `news_notifier.py` — Fetch TE news, dedupe, Discord POST.
- `run_news_notifier.py` — Entrypoint: load config, run notifier, save state.
- `state/seen_ids.json` — Persisted seen article IDs (created at first run; gitignored).
