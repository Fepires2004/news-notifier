"""
RSS feed fetcher for news notifier. Fetches articles from WSJ, NYT, FT, Reuters.
Returns normalized article dicts: {id, title, link, description, source}.
"""

import hashlib
import logging
import re

import feedparser

logger = logging.getLogger(__name__)

RSS_FEEDS: list[tuple[str, str]] = [
    # (source_name, feed_url)
    ("WSJ Markets", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"),
    ("WSJ Economy", "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed"),
    ("WSJ US Business", "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness"),
    ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ("NYT World", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("NYT Technology", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
    ("FT Home", "https://www.ft.com/rss/home"),
    ("FT World", "https://www.ft.com/world?format=rss"),
    ("FT Global Economy", "https://www.ft.com/global-economy?format=rss"),
    # Reuters: no reliable public RSS; add via rss.app or similar if needed.
]


def _article_id(source: str, link: str) -> str:
    """Generate a stable unique ID for an RSS article. Uses hash of link."""
    h = hashlib.md5(link.encode("utf-8")).hexdigest()
    return f"rss:{source}:{h}"


def _normalize_source(name: str) -> str:
    """Slug for state key, e.g. 'WSJ Markets' -> 'wsj-markets'."""
    return name.lower().replace(" ", "-")


def fetch_rss_articles(limit_per_feed: int = 15) -> list[dict]:
    """
    Fetch articles from all configured RSS feeds. Returns list of dicts:
    {id, title, link, description, source}.
    """
    articles: list[dict] = []
    for source_name, url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(url, request_headers={"User-Agent": "NewsNotifier/1.0"})
            if parsed.bozo and not parsed.entries:
                logger.warning("RSS feed %s (%s) parse error or empty.", source_name, url)
                continue
            slug = _normalize_source(source_name)
            for i, entry in enumerate(parsed.entries):
                if i >= limit_per_feed:
                    break
                link = (entry.get("link") or "").strip()
                if not link:
                    continue
                title = (entry.get("title") or "No title").strip()
                description = None
                if hasattr(entry, "summary") and entry.summary:
                    desc = re.sub(r"<[^>]+>", "", str(entry.summary))
                    description = (desc or "").strip() or None
                aid = _article_id(slug, link)
                articles.append({
                    "id": aid,
                    "title": title,
                    "link": link,
                    "description": description,
                    "source": source_name,
                })
        except Exception as e:
            logger.warning("Failed to fetch RSS %s (%s): %s", source_name, url, e)
    return articles
