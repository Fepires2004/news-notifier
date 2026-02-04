# Roadmap

## Implemented

- **TradingEconomics news to Discord notifications** — Script that fetches TradingEconomics news via their API, deduplicates by article ID, and sends notifications with direct links to Discord (and thus to your phone). Run on a schedule (cron or launchd).

## Optional later extensions

- Filtering by country or category (e.g. United States, Commodity).
- Filtering by TE `importance` field (e.g. high-importance only).
- RSS support if another feed or bridge is added; reuse same Discord + state logic.
