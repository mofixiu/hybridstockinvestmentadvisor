"""Compatibility entry point for the verified NGX end-of-day ingestion job.

This module intentionally has no model or sentiment side effects. Market bars
are ingested first; a separately validated signal process may consume them.
"""

from src.data.ngx_provider import fetch_end_of_day
from scripts.ingest_market_data import upsert_bars


def fetch_live_data() -> int:
    """Retain the old callable name while fetching daily closing data only."""
    bars = fetch_end_of_day()
    return upsert_bars(bars)


if __name__ == "__main__":
    count = fetch_live_data()
    print(f"Stored {count} verified NGX end-of-day bar(s).")
