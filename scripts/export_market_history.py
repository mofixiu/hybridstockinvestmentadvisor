"""Export authorized, verified NGX daily bars for local feature research."""

import os

import pandas as pd

from src.api.database import MarketDailyBar, SessionLocal
from src.data.ngx_provider import market_data_use_approved


def export_market_history(output_path: str = "data/processed/NGX_daily_bars.csv") -> int:
    if not market_data_use_approved():
        raise RuntimeError("Market-data use is not approved; export is disabled")
    db = SessionLocal()
    try:
        rows = (
            db.query(MarketDailyBar)
            .filter(MarketDailyBar.exchange == "NGX", MarketDailyBar.provider_verified.is_(True))
            .order_by(MarketDailyBar.trade_date, MarketDailyBar.symbol)
            .all()
        )
        if not rows:
            raise RuntimeError("No verified NGX history is stored yet")
        frame = pd.DataFrame(
            [
                {
                    "date": row.trade_date.isoformat(),
                    "ticker": row.symbol,
                    "open": float(row.open) if row.open is not None else None,
                    "high": float(row.high) if row.high is not None else None,
                    "low": float(row.low) if row.low is not None else None,
                    "close": float(row.close),
                    "volume": float(row.volume) if row.volume is not None else None,
                    "currency": row.currency,
                }
                for row in rows
            ]
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        frame.to_csv(output_path, index=False)
        return len(frame)
    finally:
        db.close()


if __name__ == "__main__":
    row_count = export_market_history()
    print(f"Exported {row_count} verified bars for local research.")
