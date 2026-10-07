"""Ingest authorized NGX end-of-day or historical OHLCV data into MySQL."""

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal

from src.api.database import MarketDailyBar, SessionLocal
from src.data.ngx_provider import fetch_end_of_day, fetch_history


def _validate_bar(bar: dict) -> None:
    if bar.get("exchange") != "NGX" or bar.get("currency") != "NGN":
        raise ValueError("This ingestion command currently accepts NGX/NGN data only")
    if not bar.get("provider_verified") or not bar.get("source"):
        raise ValueError("Only provider-verified, provenance-tagged rows can be ingested")
    close = float(bar["close"])
    if close <= 0:
        raise ValueError(f"Invalid closing price for {bar.get('symbol')}")
    high = bar.get("high")
    low = bar.get("low")
    if high is not None and low is not None and float(high) < float(low):
        raise ValueError(f"Invalid high/low range for {bar.get('symbol')}")


def upsert_bars(bars: list[dict]) -> int:
    for bar in bars:
        _validate_bar(bar)
    db = SessionLocal()
    try:
        for bar in bars:
            existing = (
                db.query(MarketDailyBar)
                .filter_by(
                    exchange=bar["exchange"],
                    symbol=bar["symbol"],
                    trade_date=bar["trade_date"],
                )
                .one_or_none()
            )
            values = {
                "currency": bar["currency"],
                "open": Decimal(str(bar["open"])) if bar["open"] is not None else None,
                "high": Decimal(str(bar["high"])) if bar["high"] is not None else None,
                "low": Decimal(str(bar["low"])) if bar["low"] is not None else None,
                "close": Decimal(str(bar["close"])),
                "volume": Decimal(str(bar["volume"])) if bar["volume"] is not None else None,
                "source": bar["source"],
                "source_as_of": bar["source_as_of"],
                "provider_verified": True,
                "ingested_at": datetime.now(timezone.utc).replace(tzinfo=None),
            }
            if existing is None:
                db.add(MarketDailyBar(**{
                    "exchange": bar["exchange"],
                    "symbol": bar["symbol"],
                    "trade_date": bar["trade_date"],
                    **values,
                }))
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
        db.commit()
        return len(bars)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-symbol", help="Backfill one NGX symbol instead of today's EOD snapshot")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    if args.history_symbol:
        if not args.start_date:
            parser.error("--history-symbol requires --start-date (YYYY-MM-DD)")
        bars = fetch_history(args.history_symbol, args.start_date, args.end_date)
    else:
        if args.start_date:
            parser.error("--start-date is only valid with --history-symbol")
        bars = fetch_end_of_day()
    if not bars:
        print("No valid market bars returned; the database was not changed.")
        return
    count = upsert_bars(bars)
    print(f"Stored {count} verified NGX bar(s) from {bars[0]['source']}.")


if __name__ == "__main__":
    main()
