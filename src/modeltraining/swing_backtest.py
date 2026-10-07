"""Chronological, purged evaluation for 5/10/20-session NGX research signals."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import balanced_accuracy_score, brier_score_loss
from sklearn.model_selection import TimeSeriesSplit


HORIZONS = (5, 10, 20)
MODEL_VERSION = "price_only_hgb_10d_v1"
FEATURE_COLUMNS = (
    "RSI",
    "EMA_50",
    "EMA_200",
    "MACD",
    "MACD_SIGNAL",
    "MACD_HIST",
    "BB_WIDTH_PCT",
    "VOLUME_MA_20",
)


def evaluate_horizon(
    frame: pd.DataFrame,
    benchmark: pd.DataFrame,
    horizon: int,
    round_trip_cost_bps: float,
    splits: int = 3,
) -> dict:
    target_column = f"Target_{horizon}"
    return_column = f"ForwardReturnPct_{horizon}"
    usable = frame.dropna(subset=[target_column, return_column, *FEATURE_COLUMNS]).copy()
    usable["date"] = pd.to_datetime(usable["date"]).dt.date
    usable[target_column] = usable[target_column].astype(int)
    dates = np.array(sorted(usable["date"].unique()), dtype=object)
    if len(dates) <= horizon + splits:
        return {"horizon_sessions": horizon, "status": "insufficient_history", "samples": len(usable)}

    benchmark = benchmark.copy()
    benchmark["date"] = pd.to_datetime(benchmark["date"]).dt.date
    benchmark = benchmark.sort_values("date").drop_duplicates("date", keep="last")
    benchmark[f"ForwardReturnPct_{horizon}"] = (
        benchmark["close"].shift(-horizon) / benchmark["close"] - 1
    ) * 100
    benchmark_returns = benchmark.set_index("date")[f"ForwardReturnPct_{horizon}"].to_dict()

    splitter = TimeSeriesSplit(n_splits=splits)
    fold_results = []
    all_y, all_probabilities, all_baseline_probabilities = [], [], []
    selected_returns, selected_benchmark_returns, all_benchmark_returns = [], [], []
    cost_pct = round_trip_cost_bps / 100.0

    for train_date_indices, test_date_indices in splitter.split(dates):
        test_start_index = int(test_date_indices[0])
        # Purge the full target horizon before each test fold so no training
        # label observes prices from the test period.
        last_train_index = test_start_index - horizon - 1
        if last_train_index < 0:
            continue
        train_dates = set(dates[: last_train_index + 1])
        test_dates = set(dates[test_date_indices])
        train = usable[usable["date"].isin(train_dates)]
        test = usable[usable["date"].isin(test_dates)]
        if train.empty or test.empty or train[target_column].nunique() < 2:
            continue

        x_train = train.loc[:, FEATURE_COLUMNS].astype(float)
        y_train = train[target_column]
        x_test = test.loc[:, FEATURE_COLUMNS].astype(float)
        y_test = test[target_column].to_numpy(dtype=int)

        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=100,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=42,
        )
        reference = DummyClassifier(strategy="prior")
        model.fit(x_train, y_train)
        reference.fit(x_train, y_train)
        positive_index = list(model.classes_).index(1)
        probabilities = model.predict_proba(x_test)[:, positive_index]
        baseline_probabilities = reference.predict_proba(x_test)[:, positive_index]
        predictions = (probabilities >= 0.5).astype(int)

        scored = test[["date", return_column]].copy()
        scored["probability_positive"] = probabilities
        scored["target"] = y_test
        scored["benchmark_return_pct"] = scored["date"].map(benchmark_returns)
        scored = scored.dropna(subset=["benchmark_return_pct"])
        selected = scored[scored["probability_positive"] >= 0.5]
        selected_returns.extend((selected[return_column] - cost_pct).tolist())
        selected_benchmark_returns.extend(
            (selected["benchmark_return_pct"] - cost_pct).tolist()
        )
        all_benchmark_returns.extend((scored["benchmark_return_pct"] - cost_pct).tolist())
        all_y.extend(y_test.tolist())
        all_probabilities.extend(probabilities.tolist())
        all_baseline_probabilities.extend(baseline_probabilities.tolist())
        fold_results.append(
            {
                "train_end": max(train_dates).isoformat(),
                "test_start": min(test_dates).isoformat(),
                "test_end": max(test_dates).isoformat(),
                "train_samples": int(len(train)),
                "test_samples": int(len(test)),
            }
        )

    if not all_y:
        return {"horizon_sessions": horizon, "status": "insufficient_fold_data", "folds": fold_results}

    brier = float(brier_score_loss(all_y, all_probabilities))
    baseline_brier = float(brier_score_loss(all_y, all_baseline_probabilities))
    model_mean = float(np.mean(selected_returns)) if selected_returns else None
    matched_benchmark_mean = (
        float(np.mean(selected_benchmark_returns)) if selected_benchmark_returns else None
    )
    benchmark_mean = float(np.mean(all_benchmark_returns)) if all_benchmark_returns else None
    return {
        "horizon_sessions": horizon,
        "status": "review_required",
        "samples": len(all_y),
        "signal_samples": len(selected_returns),
        "brier_score": brier,
        "prior_baseline_brier_score": baseline_brier,
        "balanced_accuracy": float(balanced_accuracy_score(all_y, np.array(all_probabilities) >= 0.5)),
        "mean_net_signal_return_pct": model_mean,
        "mean_net_benchmark_return_pct": benchmark_mean,
        "mean_net_matched_benchmark_return_pct": matched_benchmark_mean,
        "mean_net_excess_vs_matched_benchmark_pct": (
            model_mean - matched_benchmark_mean
            if model_mean is not None and matched_benchmark_mean is not None
            else None
        ),
        "round_trip_cost_bps": round_trip_cost_bps,
        "folds": fold_results,
        "publication_gate": "manual_review_required; no signal is published by this report",
    }


def run_backtest(
    feature_path: str,
    benchmark_path: str,
    round_trip_cost_bps: float,
    output_path: str,
) -> dict:
    frame = pd.read_csv(feature_path)
    benchmark = pd.read_csv(benchmark_path)
    if not {"date", *FEATURE_COLUMNS}.issubset(frame.columns):
        raise ValueError("Feature file is missing required dates or price-only feature columns")
    if not {"date", "close"}.issubset(benchmark.columns):
        raise ValueError("Benchmark CSV must contain `date` and `close` columns")
    if round_trip_cost_bps < 0:
        raise ValueError("round_trip_cost_bps cannot be negative")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exchange": "NGX",
        "model_version": MODEL_VERSION,
        "primary_horizon_sessions": 10,
        "round_trip_cost_bps": round_trip_cost_bps,
        "validation_status": "review_required",
        "horizons": [
            evaluate_horizon(frame, benchmark, horizon, round_trip_cost_bps)
            for horizon in HORIZONS
        ],
        "limitations": [
            "This report is research evidence, not a live signal or guarantee.",
            "Benchmark history and transaction-cost assumptions must match the intended market and account.",
            "Overlapping forward-return observations are not a compounded portfolio simulation.",
        ],
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2, allow_nan=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default="data/processed/FINAL_TRAINING_DATA_WITH_FEATURES.csv")
    parser.add_argument("--benchmark", required=True, help="CSV with the relevant index `date,close` series")
    parser.add_argument(
        "--round-trip-cost-bps",
        required=True,
        type=float,
        help="documented round-trip fees/slippage in basis points; no hidden default is used",
    )
    parser.add_argument(
        "--output",
        default=f"data/reports/swing_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    args = parser.parse_args()
    report = run_backtest(args.features, args.benchmark, args.round_trip_cost_bps, args.output)
    print(json.dumps(report, indent=2))
    print(f"Saved review-only report to {args.output}")


if __name__ == "__main__":
    main()
