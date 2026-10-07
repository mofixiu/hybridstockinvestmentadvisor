"""Train and chronologically evaluate a research-only NGX swing model.

Investo price bars are fetched into process memory only. This command writes a
derived metrics report and an unapproved model candidate, never a raw price
file or a published signal.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone

import joblib
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import HistGradientBoostingClassifier

from src.data import investo_provider
from src.modeltraining.swing_backtest import (
    FEATURE_COLUMNS,
    HORIZONS,
    MODEL_VERSION,
    evaluate_horizon,
)
from src.processing.feature_engineering import add_swing_features


def _parse_symbols(value: str | None) -> list[str] | None:
    if not value:
        return None
    symbols = sorted({part.strip().upper() for part in value.split(",") if part.strip()})
    if not symbols:
        raise ValueError("--symbols must include at least one NGX symbol")
    return symbols


def _fetch_history(symbols: list[str], start_date: date) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict] = []
    failed: list[str] = []
    for symbol in symbols:
        try:
            # Keep provider rows transient. Do not write these raw records to disk.
            rows.extend(
                {
                    "date": bar["trade_date"],
                    "ticker": symbol,
                    "close": bar["close"],
                    "volume": bar["volume"],
                }
                for bar in investo_provider.fetch_history(symbol, start_date)
            )
        except (investo_provider.InvestoProviderError, ValueError):
            failed.append(symbol)
    if not rows:
        raise RuntimeError("Investo returned no usable NGX price history")
    raw = pd.DataFrame(rows)
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["ticker"] = raw["ticker"].astype(str)
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw["volume"] = pd.to_numeric(raw["volume"], errors="coerce")
    raw = raw.dropna(subset=["date", "ticker", "close"])
    raw = raw.sort_values(["ticker", "date"]).drop_duplicates(
        ["ticker", "date"], keep="last"
    )
    if raw.empty:
        raise RuntimeError("Investo history contained no valid dated closing prices")
    features = pd.concat(
        [add_swing_features(group) for _, group in raw.groupby("ticker", sort=True)],
        ignore_index=True,
    )
    features = features.dropna(subset=["RSI", "EMA_50", "EMA_200"])
    return features, failed


def train_from_investo(
    *,
    round_trip_cost_bps: float,
    start_date: date,
    requested_symbols: list[str] | None = None,
    output_dir: str = "data/reports",
    model_dir: str = "models/research_only",
) -> dict:
    if round_trip_cost_bps < 0:
        raise ValueError("round-trip costs cannot be negative")

    stocks, _meta = investo_provider.fetch_stocks() if requested_symbols is None else ([], {})
    symbols = requested_symbols or [row["symbol"] for row in stocks]
    symbols = sorted(set(symbols))
    if not symbols:
        raise RuntimeError("Investo did not return an NGX stock universe")

    features, failed_symbols = _fetch_history(symbols, start_date)
    benchmark_rows = investo_provider.fetch_asi_history(start_date)
    benchmark = pd.DataFrame(benchmark_rows)
    if benchmark.empty or not {"date", "close"}.issubset(benchmark.columns):
        raise RuntimeError("Investo returned no usable All-Share Index benchmark history")
    benchmark["date"] = pd.to_datetime(benchmark["date"], errors="coerce")
    benchmark["close"] = pd.to_numeric(benchmark["close"], errors="coerce")
    benchmark = benchmark.dropna(subset=["date", "close"]).sort_values("date")

    horizons = [
        evaluate_horizon(features, benchmark, horizon, round_trip_cost_bps)
        for horizon in HORIZONS
    ]
    primary = next(
        (item for item in horizons if item["horizon_sessions"] == 10),
        {"status": "missing"},
    )
    latest_input_date = pd.to_datetime(features["date"]).max().date()
    generated_at = datetime.now(timezone.utc)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"investo_swing_backtest_{stamp}.json")
    model_path = os.path.join(model_dir, f"{MODEL_VERSION}_{stamp}.joblib")
    metadata_path = os.path.join(model_dir, f"{MODEL_VERSION}_{stamp}.json")

    report = {
        "generated_at": generated_at.isoformat(),
        "exchange": "NGX",
        "currency": "NGN",
        "source": investo_provider.SOURCE_NAME,
        "source_history_start": start_date.isoformat(),
        "latest_input_date": latest_input_date.isoformat(),
        "model_version": MODEL_VERSION,
        "primary_horizon_sessions": 10,
        "round_trip_cost_bps": round_trip_cost_bps,
        "symbols_requested": len(symbols),
        "symbols_with_history": int(features["ticker"].nunique()),
        "symbols_skipped": failed_symbols,
        "raw_price_history_persisted": False,
        "validation_status": "review_required",
        "horizons": horizons,
        "training_artifact": None,
        "limitations": [
            "Research candidate only; this command does not publish app signals.",
            "Raw provider prices are held in memory and are not written to disk or the database.",
            "The round-trip cost is an operator-supplied assumption and must reflect intended fees and slippage.",
            "Overlapping forward-return observations are not a compounded portfolio simulation.",
        ],
    }

    # Do not create an artifact unless the chronological 10-session evaluation
    # produced usable folds and the final training labels contain both classes.
    target = "Target_10"
    usable = features.dropna(subset=[target, *FEATURE_COLUMNS]).copy()
    if primary.get("status") == "review_required" and usable[target].nunique() == 2:
        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=100,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=42,
        )
        model.fit(usable.loc[:, FEATURE_COLUMNS].astype(float), usable[target].astype(int))
        joblib.dump(model, model_path)
        metadata = {
            "model_version": MODEL_VERSION,
            "status": "research_candidate_unapproved",
            "exchange": "NGX",
            "currency": "NGN",
            "source": investo_provider.SOURCE_NAME,
            "trained_at": generated_at.isoformat(),
            "latest_input_date": latest_input_date.isoformat(),
            "horizon_sessions": 10,
            "features": list(FEATURE_COLUMNS),
            "training_samples": int(len(usable)),
            "symbols": int(usable["ticker"].nunique()),
            "raw_price_history_persisted": False,
            "published": False,
            "backtest_report": report_path,
        }
        with open(metadata_path, "w", encoding="utf-8") as metadata_file:
            json.dump(metadata, metadata_file, indent=2, allow_nan=False)
        report["training_artifact"] = {
            "status": metadata["status"],
            "model_path": model_path,
            "metadata_path": metadata_path,
            "training_samples": metadata["training_samples"],
        }
    else:
        report["limitations"].append(
            "No final artifact was fitted because the 10-session validation or training labels were insufficient."
        )

    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, allow_nan=False)
    return {"report": report, "report_path": report_path}


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--round-trip-cost-bps",
        type=float,
        required=True,
        help="documented total round-trip fees and slippage in basis points",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2016, 1, 1),
        help="first history date (default: 2016-01-01)",
    )
    parser.add_argument(
        "--symbols",
        help="optional comma-separated NGX symbols; otherwise use Investo's listed equities",
    )
    args = parser.parse_args()
    result = train_from_investo(
        round_trip_cost_bps=args.round_trip_cost_bps,
        start_date=args.start_date,
        requested_symbols=_parse_symbols(args.symbols),
    )
    print(json.dumps(result, indent=2))
    print(f"Saved derived validation report to {result['report_path']}")


if __name__ == "__main__":
    main()
