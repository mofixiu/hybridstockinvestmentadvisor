"""Create and score paper-only NGX predictions using transient Investo history.

Raw prices, volumes, and engineered feature rows stay in process memory. Only
derived paper predictions and realized percentage returns are written to the
configured database; the report contains aggregate validation metrics.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from scripts.paper_track_signals import paper_track_report
from src.api.database import PaperSignal, SessionLocal
from src.api.market_data import is_stale, market_data_enabled
from src.data import investo_provider
from src.modeltraining.swing_backtest import FEATURE_COLUMNS, MODEL_VERSION
from src.processing.feature_engineering import add_swing_features

HORIZON_SESSIONS = 10
DEFAULT_START_DATE = date(2016, 1, 1)


def _parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    symbols = sorted({part.strip().upper() for part in value.split(",") if part.strip()})
    if not symbols:
        raise ValueError("--symbols must include at least one NGX symbol")
    return symbols


def _fetch_transient_histories(
    start_date: date, requested_symbols: list[str] | None
) -> tuple[dict[str, list[dict]], list[str], int]:
    if requested_symbols is None:
        stocks, _meta = investo_provider.fetch_stocks()
        symbols = sorted({str(row["symbol"]).strip().upper() for row in stocks if row.get("symbol")})
    else:
        symbols = sorted(set(requested_symbols))
    if not symbols:
        raise RuntimeError("Investo returned no NGX equities")

    histories: dict[str, list[dict]] = {}
    failed: list[str] = []
    for symbol in symbols:
        try:
            bars = investo_provider.fetch_history(symbol, start_date)
        except (investo_provider.InvestoProviderError, ValueError):
            failed.append(symbol)
            continue
        # Do not retain provider responses outside this process or cache window.
        verified = [
            bar for bar in bars
            if bar.get("exchange") == "NGX"
            and bar.get("currency") == "NGN"
            and bar.get("provider_verified") is True
            and bar.get("source") == investo_provider.SOURCE_NAME
            and bar.get("close") is not None
            and float(bar["close"]) > 0
        ]
        verified.sort(key=lambda row: row["trade_date"])
        if verified:
            histories[symbol] = verified
    return histories, failed, len(symbols)


def _feature_frame(histories: dict[str, list[dict]]) -> pd.DataFrame:
    rows = [
        {
            "date": bar["trade_date"],
            "ticker": symbol,
            "close": bar["close"],
            "volume": bar["volume"],
        }
        for symbol, bars in histories.items()
        for bar in bars
    ]
    if not rows:
        return pd.DataFrame()
    raw = pd.DataFrame(rows)
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw["volume"] = pd.to_numeric(raw["volume"], errors="coerce")
    raw = raw.dropna(subset=["date", "ticker", "close"])
    raw = raw.sort_values(["ticker", "date"]).drop_duplicates(
        ["ticker", "date"], keep="last"
    )
    if raw.empty:
        return pd.DataFrame()
    frame = pd.concat(
        [add_swing_features(group) for _, group in raw.groupby("ticker", sort=True)],
        ignore_index=True,
    )
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["OutcomeDate_10"] = pd.to_datetime(
        frame["OutcomeDate_10"], errors="coerce"
    ).dt.date
    return frame


def _score_matured_signals(db, histories: dict[str, list[dict]]) -> int:
    open_signals = (
        db.query(PaperSignal)
        .filter(
            PaperSignal.exchange == "NGX",
            PaperSignal.model_version == MODEL_VERSION,
            PaperSignal.validation_status == "paper",
            PaperSignal.realized_return_pct.is_(None),
        )
        .all()
    )
    evaluated = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for signal in open_signals:
        bars = histories.get(signal.symbol, [])
        start = next(
            (bar for bar in bars if bar["trade_date"] == signal.signal_date), None
        )
        if start is None or float(start["close"]) <= 0:
            continue
        future = [bar for bar in bars if bar["trade_date"] > signal.signal_date]
        if len(future) < signal.horizon_sessions:
            continue
        outcome_close = float(future[signal.horizon_sessions - 1]["close"])
        signal.realized_return_pct = Decimal(
            str((outcome_close / float(start["close"]) - 1) * 100)
        )
        signal.evaluated_at = now
        evaluated += 1
    if evaluated:
        db.commit()
    return evaluated


def _record_latest_predictions(
    db,
    frame: pd.DataFrame,
    histories: dict[str, list[dict]],
    *,
    minimum_training_samples: int,
) -> tuple[int, int, int]:
    if frame.empty:
        return 0, 0, 0
    label_column = "Target_10"
    completed = frame.dropna(
        subset=[label_column, "OutcomeDate_10", *FEATURE_COLUMNS]
    ).copy()
    completed[label_column] = completed[label_column].astype(int)

    candidates: dict[date, list[tuple[str, dict, pd.Series]]] = {}
    stale = 0
    for symbol, bars in histories.items():
        latest_bar = bars[-1]
        if is_stale(latest_bar["trade_date"]):
            stale += 1
            continue
        latest = frame[
            (frame["ticker"] == symbol) & (frame["date"] == latest_bar["trade_date"])
        ].dropna(subset=list(FEATURE_COLUMNS))
        if latest.empty:
            continue
        candidates.setdefault(latest_bar["trade_date"], []).append(
            (symbol, latest_bar, latest.iloc[-1])
        )

    recorded = 0
    skipped = stale
    for signal_date, rows in sorted(candidates.items()):
        # Train only with labels whose ten-session outcome was already known
        # at the timestamp of the candidate close.
        training = completed[completed["OutcomeDate_10"] <= signal_date]
        if len(training) < minimum_training_samples or training[label_column].nunique() < 2:
            skipped += len(rows)
            continue
        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=100,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=42,
        )
        model.fit(
            training.loc[:, FEATURE_COLUMNS].astype(float),
            training[label_column].astype(int),
        )
        positive_index = list(model.classes_).index(1)
        prior_probability = float(training[label_column].mean())

        for symbol, bar, candidate in rows:
            key = {
                "exchange": "NGX",
                "symbol": symbol,
                "signal_date": signal_date,
                "horizon_sessions": HORIZON_SESSIONS,
                "model_version": MODEL_VERSION,
            }
            if db.query(PaperSignal).filter_by(**key).first() is not None:
                skipped += 1
                continue
            x = candidate.loc[list(FEATURE_COLUMNS)].astype(float).to_frame().T
            probability = float(model.predict_proba(x)[0, positive_index])
            if not np.isfinite(probability) or np.isclose(probability, 0.5, atol=1e-12):
                skipped += 1
                continue
            direction = "positive" if probability > 0.5 else "negative"
            trend = "above" if float(candidate["MACD_HIST"]) >= 0 else "below"
            ema_position = (
                "above" if float(candidate["EMA_50"]) >= float(candidate["EMA_200"])
                else "below"
            )
            evidence = [
                f"Price-only model probability of a positive 10-session return: {probability:.3f}",
                f"Training-period prior positive-return rate: {prior_probability:.3f}",
                f"RSI-14: {float(candidate['RSI']):.1f}; MACD histogram is {trend} zero; EMA-50 is {ema_position} EMA-200",
            ]
            source_as_of = bar["source_as_of"]
            if source_as_of.tzinfo is not None:
                source_as_of = source_as_of.astimezone(timezone.utc).replace(tzinfo=None)
            db.add(
                PaperSignal(
                    **key,
                    direction=direction,
                    probability_positive=Decimal(str(probability)),
                    prior_probability_positive=Decimal(str(prior_probability)),
                    validation_status="paper",
                    evidence_json=json.dumps(evidence),
                    source_as_of=source_as_of,
                )
            )
            recorded += 1
    if recorded:
        db.commit()
    candidate_count = sum(len(rows) for rows in candidates.values())
    return recorded, skipped, candidate_count


def run_paper_tracking(
    *,
    round_trip_cost_bps: float,
    start_date: date = DEFAULT_START_DATE,
    requested_symbols: list[str] | None = None,
    minimum_training_samples: int = 100,
    output_path: str = "data/reports/paper_track_latest.json",
) -> dict:
    if not market_data_enabled() or not investo_provider.is_configured():
        raise ValueError("Configure the Investo API key before running paper tracking")
    if round_trip_cost_bps < 0:
        raise ValueError("round-trip costs cannot be negative")
    if minimum_training_samples < 30:
        raise ValueError("minimum_training_samples must be at least 30")

    histories, failed_symbols, symbols_requested = _fetch_transient_histories(
        start_date, requested_symbols
    )
    frame = _feature_frame(histories)
    db = SessionLocal()
    try:
        evaluated = _score_matured_signals(db, histories)
        recorded, skipped, symbols_with_candidates = _record_latest_predictions(
            db,
            frame,
            histories,
            minimum_training_samples=minimum_training_samples,
        )
        report = paper_track_report(db, round_trip_cost_bps)
        current_model_signals = (
            db.query(PaperSignal)
            .filter(
                PaperSignal.exchange == "NGX",
                PaperSignal.model_version == MODEL_VERSION,
                PaperSignal.validation_status == "paper",
            )
            .all()
        )
    finally:
        db.close()

    report["source"] = investo_provider.SOURCE_NAME
    report["model_version"] = MODEL_VERSION
    report["primary_horizon_sessions"] = HORIZON_SESSIONS
    report["symbols_requested"] = symbols_requested
    report["symbols_with_history"] = len(histories)
    report["symbols_failed"] = failed_symbols
    report["symbols_with_candidates"] = symbols_with_candidates
    report["paper_signals_recorded_this_run"] = recorded
    report["paper_signals_scored_this_run"] = evaluated
    report["paper_signals_total"] = len(current_model_signals)
    report["paper_signals_open"] = sum(
        signal.realized_return_pct is None for signal in current_model_signals
    )
    report["paper_signals_matured"] = sum(
        signal.realized_return_pct is not None for signal in current_model_signals
    )
    report["symbols_or_rows_skipped"] = skipped
    report["raw_price_history_persisted"] = False
    report["publication_gate"] = (
        "Paper predictions are never published automatically; approval requires a separate review."
    )
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round-trip-cost-bps", required=True, type=float)
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_START_DATE)
    parser.add_argument("--symbols", help="optional comma-separated NGX symbol list")
    parser.add_argument("--minimum-training-samples", type=int, default=100)
    parser.add_argument("--output", default="data/reports/paper_track_latest.json")
    args = parser.parse_args()
    report = run_paper_tracking(
        round_trip_cost_bps=args.round_trip_cost_bps,
        start_date=args.start_date,
        requested_symbols=_parse_symbols(args.symbols),
        minimum_training_samples=args.minimum_training_samples,
        output_path=args.output,
    )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
