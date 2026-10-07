"""Train on matured verified NGX history and record paper-only 10-day predictions."""

from __future__ import annotations

import argparse
from datetime import date

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from scripts.record_paper_signal import record_paper_signal
from src.api.database import MarketDailyBar, SessionLocal
from src.api.market_data import is_stale, market_data_enabled
from src.modeltraining.swing_backtest import FEATURE_COLUMNS, MODEL_VERSION
from src.processing.feature_engineering import add_swing_features

MIN_TRAINING_SAMPLES = 100
HORIZON_SESSIONS = 10


def _training_frame(db) -> tuple[pd.DataFrame, dict[str, MarketDailyBar]]:
    bars = (
        db.query(MarketDailyBar)
        .filter(
            MarketDailyBar.exchange == "NGX",
            MarketDailyBar.currency == "NGN",
            MarketDailyBar.provider_verified.is_(True),
            MarketDailyBar.source.is_not(None),
            MarketDailyBar.source != "",
        )
        .order_by(MarketDailyBar.symbol, MarketDailyBar.trade_date)
        .all()
    )
    if not bars:
        return pd.DataFrame(), {}

    rows = [
        {
            "date": bar.trade_date,
            "ticker": bar.symbol,
            "close": float(bar.close),
            "volume": float(bar.volume) if bar.volume is not None else np.nan,
        }
        for bar in bars
        if bar.close is not None and float(bar.close) > 0
    ]
    market = pd.DataFrame(rows)
    if market.empty:
        return pd.DataFrame(), {}
    engineered = pd.concat(
        [
            add_swing_features(group)
            for _, group in market.groupby("ticker", sort=True)
        ],
        ignore_index=True,
    )
    latest_bars = {}
    for bar in bars:
        current = latest_bars.get(bar.symbol)
        if current is None or bar.trade_date > current.trade_date:
            latest_bars[bar.symbol] = bar
    return engineered, latest_bars


def generate_paper_predictions(
    db,
    *,
    minimum_training_samples: int = MIN_TRAINING_SAMPLES,
    as_of_date: date | None = None,
) -> dict:
    """Record fresh latest-close outputs as paper predictions, never published signals."""
    if not market_data_enabled():
        raise ValueError("Market-data use is not configured and approved")
    if minimum_training_samples < 30:
        raise ValueError("minimum_training_samples must be at least 30")

    frame, latest_bars = _training_frame(db)
    if frame.empty:
        return {"model_version": MODEL_VERSION, "recorded": 0, "skipped": 0, "reason": "no_verified_history"}

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["OutcomeDate_10"] = pd.to_datetime(frame["OutcomeDate_10"], errors="coerce").dt.date
    label_column = "Target_10"
    completed = frame.dropna(
        subset=[label_column, "OutcomeDate_10", *FEATURE_COLUMNS]
    ).copy()
    completed[label_column] = completed[label_column].astype(int)

    recorded = 0
    skipped = 0
    for symbol, bar in latest_bars.items():
        if as_of_date is not None and bar.trade_date > as_of_date:
            skipped += 1
            continue
        if bar.exchange != "NGX" or not bar.provider_verified or not bar.source or is_stale(bar.trade_date):
            skipped += 1
            continue

        latest_rows = frame[
            (frame["ticker"] == symbol) & (frame["date"] == bar.trade_date)
        ].dropna(subset=list(FEATURE_COLUMNS))
        if latest_rows.empty:
            skipped += 1
            continue
        candidate = latest_rows.iloc[-1]

        # A label is eligible only if all ten future closes used to create it
        # were already observed by this candidate signal's closing date.
        train = completed[completed["OutcomeDate_10"] <= bar.trade_date]
        if len(train) < minimum_training_samples or train[label_column].nunique() < 2:
            skipped += 1
            continue

        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=100,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=42,
        )
        x_train = train.loc[:, FEATURE_COLUMNS].astype(float)
        y_train = train[label_column].astype(int)
        model.fit(x_train, y_train)
        positive_index = list(model.classes_).index(1)
        probability = float(model.predict_proba(candidate.loc[list(FEATURE_COLUMNS)].astype(float).to_frame().T)[0, positive_index])
        if not np.isfinite(probability) or np.isclose(probability, 0.5, atol=1e-12):
            skipped += 1
            continue
        prior_probability = float(y_train.mean())
        direction = "positive" if probability >= 0.5 else "negative"
        rsi = float(candidate["RSI"])
        trend = "above" if float(candidate["MACD_HIST"]) >= 0 else "below"
        ema_position = "above" if float(candidate["EMA_50"]) >= float(candidate["EMA_200"]) else "below"
        evidence = (
            f"Price-only model probability of a positive 10-session return: {probability:.3f}",
            f"Training-period prior positive-return rate: {prior_probability:.3f}",
            f"RSI-14: {rsi:.1f}; MACD histogram is {trend} zero; EMA-50 is {ema_position} EMA-200",
        )
        try:
            record_paper_signal(
                db,
                symbol=symbol,
                direction=direction,
                probability_positive=probability,
                prior_probability_positive=prior_probability,
                model_version=MODEL_VERSION,
                evidence="; ".join(evidence),
                horizon_sessions=HORIZON_SESSIONS,
            )
            recorded += 1
        except ValueError as exc:
            if "already has a paper signal" in str(exc):
                skipped += 1
                continue
            raise

    return {
        "model_version": MODEL_VERSION,
        "horizon_sessions": HORIZON_SESSIONS,
        "training_samples_minimum": minimum_training_samples,
        "recorded": recorded,
        "skipped": skipped,
        "validation_status": "paper_only_review_required",
        "publication_gate": "paper predictions are never published automatically",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimum-training-samples", type=int, default=MIN_TRAINING_SAMPLES)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        result = generate_paper_predictions(
            db, minimum_training_samples=args.minimum_training_samples
        )
    finally:
        db.close()
    print(pd.Series(result).to_json(indent=2))


if __name__ == "__main__":
    main()
