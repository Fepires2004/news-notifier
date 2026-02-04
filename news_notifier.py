"""
News notifier: fetches from TradingEconomics API and RSS feeds (WSJ, NYT, FT, Reuters),
deduplicates by article ID, and posts new items to a Discord webhook.
"""

import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from rss_feeds import fetch_rss_articles

load_dotenv()

logger = logging.getLogger(__name__)

TE_BASE_URL = "https://tradingeconomics.com"
TE_API_URL = "https://api.tradingeconomics.com/news"
MAX_SEEN_IDS = 3000  # Increased for multi-source
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
    """Load set of seen article IDs from state file. Migrates legacy TE ids to te: prefix."""
    if not state_path.exists():
        return set()
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids = data.get("ids", data) if isinstance(data, dict) else data
        result: set[str] = set()
        for i in ids:
            s = str(i)
            if s and ":" not in s and s.isdigit():
                result.add(f"te:{s}")  # Migrate legacy TE ids
            else:
                result.add(s)
        return result
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


def send_discord_notification(
    webhook_url: str,
    title: str,
    link: str,
    description: str | None = None,
    source: str | None = None,
) -> bool:
    """
    POST a single notification to the Discord webhook. Uses content (title + link)
    and optionally an embed. Returns True on success.
    """
    prefix = f"[{source}] " if source else ""
    content = f"{prefix}{title}\n{link}"
    payload = {"content": content}
    embed_title = f"{prefix}{title}" if prefix else title
    if description:
        snippet = (description[:200] + "…") if len(description) > 200 else description
        payload["embeds"] = [
            {
                "title": embed_title,
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
    rss_enabled: bool | None = None,
) -> None:
    """
    Main flow: load seen IDs, fetch TE + RSS news, for each new article post to Discord
    and add ID to seen set, then persist seen IDs.
    """
    if rss_enabled is None:
        rss_enabled = os.getenv("RSS_ENABLED", "true").lower() not in ("false", "0", "no")
    webhook = (discord_webhook_url or get_discord_webhook_url()).strip()
    if not webhook:
        logger.error("DISCORD_WEBHOOK_URL is not set. Set it in .env or pass discord_webhook_url.")
        return

    key = te_api_key or get_te_api_key()
    path = state_path or get_state_path()
    seen = load_seen_ids(path)

    # Fetch TradingEconomics articles
    te_items = fetch_te_news(key, limit=limit)
    articles: list[dict] = []
    for item in te_items:
        aid = item.get("id")
        if aid is None:
            continue
        aid_str = f"te:{aid}"
        rel_url = item.get("url") or ""
        link = article_full_url(rel_url)
        articles.append({
            "id": aid_str,
            "title": item.get("title") or "No title",
            "link": link,
            "description": item.get("description"),
            "source": "TradingEconomics",
        })

    # Fetch RSS articles
    if rss_enabled:
        rss_items = fetch_rss_articles(limit_per_feed=15)
        articles.extend(rss_items)

    # Dedupe and notify (with delay to avoid Discord rate limit ~30/min per webhook)
    for item in articles:
        aid = item.get("id", "")
        if not aid or aid in seen:
            continue
        title = item.get("title") or "No title"
        link = item.get("link") or ""
        description = item.get("description")
        source = item.get("source")
        send_discord_notification(webhook, title, link, description, source=source)
        seen.add(aid)
        time.sleep(1)  # ~1/sec to stay under Discord webhook rate limit (~30/min)

    save_seen_ids(path, seen)
