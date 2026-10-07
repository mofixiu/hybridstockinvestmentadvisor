"""Score paper-only predictions after their forward close becomes observable."""

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.api.database import MarketDailyBar, PaperSignal, SessionLocal


def evaluate_open_signals(db) -> int:
    signals = (
        db.query(PaperSignal)
        .filter(
            PaperSignal.validation_status == "paper",
            PaperSignal.realized_return_pct.is_(None),
        )
        .all()
    )
    evaluated = 0
    for signal in signals:
        bars = (
            db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.exchange == signal.exchange,
                MarketDailyBar.symbol == signal.symbol,
                MarketDailyBar.provider_verified.is_(True),
                MarketDailyBar.trade_date > signal.signal_date,
            )
            .order_by(MarketDailyBar.trade_date.asc())
            .limit(signal.horizon_sessions)
            .all()
        )
        if len(bars) < signal.horizon_sessions:
            continue
        start = (
            db.query(MarketDailyBar)
            .filter(
                MarketDailyBar.exchange == signal.exchange,
                MarketDailyBar.symbol == signal.symbol,
                MarketDailyBar.trade_date == signal.signal_date,
                MarketDailyBar.provider_verified.is_(True),
            )
            .one_or_none()
        )
        if start is None or float(start.close) <= 0:
            continue
        outcome = (float(bars[-1].close) / float(start.close) - 1) * 100
        signal.realized_return_pct = outcome
        signal.evaluated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        evaluated += 1
    if evaluated:
        db.commit()
    return evaluated


def paper_track_report(db, round_trip_cost_bps: float) -> dict:
    if round_trip_cost_bps < 0:
        raise ValueError("round_trip_cost_bps cannot be negative")
    signals = (
        db.query(PaperSignal)
        .filter(
            PaperSignal.validation_status == "paper",
            PaperSignal.realized_return_pct.is_not(None),
        )
        .all()
    )
    rows = []
    cost_pct = round_trip_cost_bps / 100
    for signal in signals:
        realized = float(signal.realized_return_pct)
        actual_positive = realized > 0
        probability_positive = float(signal.probability_positive or 0.5)
        directional = realized if signal.direction == "positive" else -realized
        rows.append(
            {
                "exchange": signal.exchange,
                "symbol": signal.symbol,
                "horizon_sessions": signal.horizon_sessions,
                "model_version": signal.model_version,
                "direction": signal.direction,
                "actual_positive": actual_positive,
                "probability_positive": probability_positive,
                "prior_probability_positive": (
                    float(signal.prior_probability_positive)
                    if signal.prior_probability_positive is not None
                    else None
                ),
                "directional_return_pct": directional,
            }
        )

    groups = {}
    keys = sorted({(r["exchange"], r["symbol"], r["horizon_sessions"], r["model_version"]) for r in rows})
    for exchange, symbol, horizon, model_version in keys:
        selected = [
            row for row in rows
            if (row["exchange"], row["symbol"], row["horizon_sessions"], row["model_version"])
            == (exchange, symbol, horizon, model_version)
        ]
        baseline_scored = [row for row in selected if row["prior_probability_positive"] is not None]
        groups[f"{exchange}:{symbol}:{horizon}:{model_version}"] = {
            "samples": len(selected),
            "baseline_samples": len(baseline_scored),
            "directional_hit_rate": float(np.mean([
                (row["direction"] == "positive") == row["actual_positive"]
                for row in selected
            ])),
            "brier_score": float(np.mean([
                (row["probability_positive"] - float(row["actual_positive"])) ** 2
                for row in selected
            ])),
            "baseline_matched_brier_score": (
                float(np.mean([
                    (row["probability_positive"] - float(row["actual_positive"])) ** 2
                    for row in baseline_scored
                ]))
                if baseline_scored
                else None
            ),
            "prior_baseline_brier_score": (
                float(np.mean([
                    (float(row["prior_probability_positive"]) - float(row["actual_positive"])) ** 2
                    for row in baseline_scored
                ]))
                if baseline_scored
                else None
            ),
            "mean_net_directional_return_pct": float(np.mean([
                row["directional_return_pct"] - cost_pct for row in selected
            ])),
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_signal_count": len(rows),
        "round_trip_cost_bps": round_trip_cost_bps,
        "groups": groups,
        "validation_status": "paper_only_review_required",
        "publication_gate": "No signal is published by this report. Compare with backtest baselines and the exchange index before any separate review.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round-trip-cost-bps", required=True, type=float)
    parser.add_argument("--output", default="data/reports/paper_track_latest.json")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        evaluated = evaluate_open_signals(db)
        report = paper_track_report(db, args.round_trip_cost_bps)
    finally:
        db.close()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
    print(f"Scored {evaluated} completed paper signal(s); saved review-only report to {args.output}")


if __name__ == "__main__":
    main()
