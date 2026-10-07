"""Leakage-aware OHLCV features and 5/10/20-session forward targets."""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

INPUT_PATH = "data/processed/NGX_daily_bars.csv"
OUTPUT_PATH = "data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv"
TARGET_HORIZONS = (5, 10, 20)


def add_swing_features(group: pd.DataFrame) -> pd.DataFrame:
    """Add price-only technical indicators and forward targets to one symbol."""
    frame = group.copy().sort_values("date").reset_index(drop=True)
    close = pd.to_numeric(frame["close"], errors="coerce")
    frame["close"] = close

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = -delta.clip(upper=0).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    frame["RSI"] = 100 - (100 / (1 + rs))
    frame.loc[(gain == 0) & (loss == 0), "RSI"] = 50
    frame.loc[(loss == 0) & (gain > 0), "RSI"] = 100
    frame.loc[(gain == 0) & (loss > 0), "RSI"] = 0

    frame["EMA_50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    frame["EMA_200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()
    ema_12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["MACD"] = ema_12 - ema_26
    frame["MACD_SIGNAL"] = frame["MACD"].ewm(span=9, adjust=False, min_periods=9).mean()
    frame["MACD_HIST"] = frame["MACD"] - frame["MACD_SIGNAL"]

    middle = close.rolling(20, min_periods=20).mean()
    deviation = close.rolling(20, min_periods=20).std()
    frame["BB_MID"] = middle
    frame["BB_UPPER"] = middle + 2 * deviation
    frame["BB_LOWER"] = middle - 2 * deviation
    frame["BB_WIDTH_PCT"] = ((frame["BB_UPPER"] - frame["BB_LOWER"]) / middle) * 100

    if "volume" in frame.columns:
        frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
        frame["VOLUME_MA_20"] = frame["volume"].rolling(20, min_periods=20).mean()
    else:
        frame["volume"] = np.nan

    for horizon in TARGET_HORIZONS:
        future_close = close.shift(-horizon)
        frame[f"OutcomeDate_{horizon}"] = pd.to_datetime(frame["date"]).shift(-horizon)
        forward_return = (future_close / close - 1) * 100
        frame[f"ForwardReturnPct_{horizon}"] = forward_return
        target = (future_close > close).astype("Int64")
        frame[f"Target_{horizon}"] = target.where(future_close.notna())

    # Compatibility for existing exploratory scripts: Target now means the
    # 10-session direction, not next-day movement.
    frame["Target"] = frame["Target_10"]
    return frame


def add_technical_indicators() -> pd.DataFrame:
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"{INPUT_PATH} not found. Run scripts/export_market_history.py after authorized ingestion."
        )
    data = pd.read_csv(INPUT_PATH)
    required = {"date", "ticker", "close"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Market history is missing required columns: {', '.join(sorted(missing))}")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date", "ticker", "close"])
    features = pd.concat(
        [add_swing_features(group) for _, group in data.groupby("ticker", sort=True)],
        ignore_index=True,
    )
    # Keep every feature-ready row, including the latest 20 sessions. Their
    # forward targets remain null until the required future closes exist.
    features = features.dropna(subset=["RSI", "EMA_50", "EMA_200"])
    features.to_csv(OUTPUT_PATH, index=False)
    return features


if __name__ == "__main__":
    result = add_technical_indicators()
    print(f"Wrote {len(result)} swing-training rows to {OUTPUT_PATH}")
