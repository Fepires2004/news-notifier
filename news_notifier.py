"""
TradingEconomics news notifier: fetch latest news via TE API, deduplicate, and
post new items to a Discord webhook with direct links to the article pages.
"""

import json
import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TE_BASE_URL = "https://tradingeconomics.com"
TE_API_URL = "https://api.tradingeconomics.com/news"
MAX_SEEN_IDS = 1000
DEFAULT_LIMIT = 20


def get_te_api_key() -> str:
    """Return TE API key from env, or guest credentials for limited access."""
    key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    return key if key else "guest:guest"


def get_discord_webhook_url() -> str:
    """Return Discord webhook URL from env. Empty if not set."""
    return (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()


def get_state_path() -> Path:
    """Path to the seen-IDs state file (under project directory)."""
    base = Path(__file__).resolve().parent
    return base / "state" / "seen_ids.json"


def load_seen_ids(state_path: Path) -> set[str]:
    """Load set of seen article IDs from state file. Returns empty set if missing or invalid."""
    if not state_path.exists():
        return set()
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids = data.get("ids", data) if isinstance(data, dict) else data
        return set(str(i) for i in ids)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load state file %s: %s", state_path, e)
        return set()


def save_seen_ids(state_path: Path, seen_ids: set[str]) -> None:
    """Persist seen IDs, keeping at most MAX_SEEN_IDS. Creates state dir if needed."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    ids_list = list(seen_ids)
    if len(ids_list) > MAX_SEEN_IDS:
        ids_list = ids_list[-MAX_SEEN_IDS:]
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"ids": ids_list}, f, indent=0)


def fetch_te_news(api_key: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """
    Fetch latest news from TradingEconomics API. Returns list of article dicts
    with id, title, date, description, url (relative), etc.
    """
    params = {"c": api_key, "f": "json", "limit": limit}
    try:
        r = requests.get(TE_API_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except requests.RequestException as e:
        logger.error("TradingEconomics API request failed: %s", e)
        return []
    except (ValueError, KeyError) as e:
        logger.error("Invalid API response: %s", e)
        return []


def article_full_url(relative_url: str) -> str:
    """Build full TradingEconomics article URL from relative path."""
    path = (relative_url or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    return TE_BASE_URL.rstrip("/") + path


def send_discord_notification(webhook_url: str, title: str, link: str, description: str | None = None) -> bool:
    """
    POST a single notification to the Discord webhook. Uses content (title + link)
    and optionally an embed. Returns True on success.
    """
    content = f"{title}\n{link}"
    payload = {"content": content}
    if description:
        snippet = (description[:200] + "…") if len(description) > 200 else description
        payload["embeds"] = [
            {
                "title": title,
                "url": link,
                "description": snippet,
                "color": 3447003,
            }
        ]
    try:
        r = requests.post(webhook_url, json=payload, timeout=10)
        if r.status_code in (200, 204):
            return True
        logger.warning("Discord webhook returned %s: %s", r.status_code, r.text[:200])
        return False
    except requests.RequestException as e:
        logger.warning("Discord webhook request failed: %s", e)
        return False


def run(
    discord_webhook_url: str | None = None,
    te_api_key: str | None = None,
    limit: int = DEFAULT_LIMIT,
    state_path: Path | None = None,
) -> None:
    """
    Main flow: load seen IDs, fetch TE news, for each new article post to Discord
    and add ID to seen set, then persist seen IDs.
    """
    webhook = (discord_webhook_url or get_discord_webhook_url()).strip()
    if not webhook:
        logger.error("DISCORD_WEBHOOK_URL is not set. Set it in .env or pass discord_webhook_url.")
        return

    key = te_api_key or get_te_api_key()
    path = state_path or get_state_path()
    seen = load_seen_ids(path)
    articles = fetch_te_news(key, limit=limit)

    for item in articles:
        aid = item.get("id")
        if aid is None:
            continue
        aid = str(aid)
        if aid in seen:
            continue
        title = item.get("title") or "No title"
        rel_url = item.get("url") or ""
        link = article_full_url(rel_url)
        description = item.get("description")
        send_discord_notification(webhook, title, link, description)
        seen.add(aid)

    save_seen_ids(path, seen)
