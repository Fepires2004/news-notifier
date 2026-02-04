# Roadmap

## Implemented

- **TradingEconomics news to Discord notifications** — Script that fetches TradingEconomics news via their API, deduplicates by article ID, and sends notifications with direct links to Discord (and thus to your phone). Run on a schedule (cron or launchd).
- **GitHub Actions 24/7** — Workflow runs every 45 min in the cloud; no laptop needed.
- **RSS feeds (WSJ, NYT, FT)** — Fetches from 9 feeds: WSJ (Markets, Economy, US Business), NYT (Business, World, Technology), FT (Home, World, Global Economy). All posts to Discord with `[Source]` prefix.

## Planned: Multi-source expansion

### RSS feeds (additional)

- **Wall Street Journal** — Official RSS via feeds.content.dowjones.io (Markets, Economy, U.S. Business, etc.). May require respecting WSJ RSS terms.
- **New York Times** — Free RSS at nytimes.com/rss (Business, World, Politics, Tech, etc.). Personal/noncommercial use only.
- **Financial Times** — RSS at ft.com/rss/home, ft.com/world?format=rss, ft.com/global-economy?format=rss.
- **Reuters** — Various RSS feeds for Markets, Finance, Breaking Views.
- **Bloomberg** — Multiple finance-related RSS feeds (Markets, Economics, Technology).

**Implementation:** Use `feedparser`; add generic RSS fetcher; deduplicate by `source:url` in state; reuse existing Discord logic.

### Other opportunities

- **Keyword/ticker filtering** — Only notify on articles matching keywords (e.g. "Fed", "inflation", "$AAPL").
- **Additional notification channels** — Telegram bot, email digest.
- **TE enhancements** — Filter by country, category, or importance (already in TE API).
- **SEC EDGAR** — Free API for filings (10-K, 8-K); could notify on filings for watched tickers.
- **Fed/ECB press releases** — Often have RSS or stable URLs; useful for macro watchers.
