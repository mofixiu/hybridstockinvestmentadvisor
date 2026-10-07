"""Approve a model version only when out-of-sample and paper gates pass."""

import argparse
import json
import math
from datetime import datetime, timezone

from src.api.database import ModelReleaseApproval, SessionLocal


def _finite_number(value, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} is missing or invalid") from None
    if not math.isfinite(number):
        raise ValueError(f"{label} is missing or invalid")
    return number


def _review_metrics(
    backtest: dict,
    paper: dict,
    *,
    exchange: str,
    symbol: str,
    model_version: str,
    minimum_paper_samples: int,
) -> dict:
    if minimum_paper_samples < 1:
        raise ValueError("minimum_paper_samples must be at least 1")
    if backtest.get("validation_status") != "review_required":
        raise ValueError("backtest report is not a completed review-required report")
    if backtest.get("exchange", "").upper() != exchange.upper():
        raise ValueError("backtest report exchange does not match the requested release")
    if backtest.get("model_version") != model_version:
        raise ValueError("backtest report model version does not match the requested release")
    if backtest.get("primary_horizon_sessions") != 10:
        raise ValueError("the primary backtest horizon must be 10 trading sessions")
    if paper.get("validation_status") != "paper_only_review_required":
        raise ValueError("paper report is not a completed paper-track report")
    if _finite_number(backtest.get("round_trip_cost_bps"), "backtest costs") != _finite_number(
        paper.get("round_trip_cost_bps"), "paper-track costs"
    ):
        raise ValueError("backtest and paper-track reports must use the same round-trip costs")

    ten_day = next(
        (
            item for item in backtest.get("horizons", [])
            if item.get("horizon_sessions") == 10
        ),
        None,
    )
    if ten_day is None or ten_day.get("status") != "review_required":
        raise ValueError("a completed 10-session walk-forward report is required")
    if int(ten_day.get("signal_samples", 0)) < 1:
        raise ValueError("the 10-session backtest produced no candidate signals")
    backtest_brier = _finite_number(ten_day.get("brier_score"), "backtest Brier score")
    backtest_baseline = _finite_number(
        ten_day.get("prior_baseline_brier_score"), "backtest baseline Brier score"
    )
    backtest_excess = _finite_number(
        ten_day.get("mean_net_excess_vs_matched_benchmark_pct"),
        "matched benchmark excess return",
    )
    if backtest_brier >= backtest_baseline or backtest_excess <= 0:
        raise ValueError("10-session backtest must beat the prior baseline and matched index after costs")

    key = f"{exchange.upper()}:{symbol.upper()}:10:{model_version}"
    paper_metrics = (paper.get("groups") or {}).get(key)
    if paper_metrics is None:
        raise ValueError(f"paper report has no completed group for {key}")
    samples = int(paper_metrics.get("samples", 0))
    if samples < minimum_paper_samples:
        raise ValueError(
            f"paper tracking has {samples} samples; {minimum_paper_samples} are required"
        )
    baseline_samples = int(paper_metrics.get("baseline_samples", 0))
    if baseline_samples < minimum_paper_samples:
        raise ValueError(
            f"paper tracking has {baseline_samples} contemporaneous baseline samples; "
            f"{minimum_paper_samples} are required"
        )
    paper_brier = _finite_number(
        paper_metrics.get("baseline_matched_brier_score"), "matched paper Brier score"
    )
    paper_baseline = _finite_number(
        paper_metrics.get("prior_baseline_brier_score"), "paper baseline Brier score"
    )
    paper_hit_rate = _finite_number(
        paper_metrics.get("directional_hit_rate"), "paper directional hit rate"
    )
    paper_return = _finite_number(
        paper_metrics.get("mean_net_directional_return_pct"), "paper net directional return"
    )
    if paper_brier >= paper_baseline or paper_hit_rate <= 0.5 or paper_return <= 0:
        raise ValueError("paper tracking must beat its prior baseline and show positive net directional results")

    return {
        "paper_sample_count": samples,
        "paper_hit_rate": paper_hit_rate,
        "paper_brier_score": paper_brier,
        "paper_prior_baseline_brier_score": paper_baseline,
        "paper_mean_net_directional_return_pct": paper_return,
        "backtest_brier_score": backtest_brier,
        "backtest_prior_baseline_brier_score": backtest_baseline,
        "backtest_mean_net_excess_vs_matched_benchmark_pct": backtest_excess,
    }


def approve_model(
    db,
    *,
    backtest: dict,
    paper: dict,
    exchange: str,
    symbol: str,
    model_version: str,
    reviewer: str,
    minimum_paper_samples: int,
) -> ModelReleaseApproval:
    exchange = exchange.strip().upper()
    symbol = symbol.strip().upper()
    model_version = model_version.strip()
    reviewer = reviewer.strip()
    if exchange != "NGX":
        raise ValueError("Only NGX model approvals are supported in this release")
    if not symbol or not model_version or not reviewer:
        raise ValueError("symbol, model_version, and reviewer are required")
    metrics = _review_metrics(
        backtest,
        paper,
        exchange=exchange,
        symbol=symbol,
        model_version=model_version,
        minimum_paper_samples=minimum_paper_samples,
    )
    key = {
        "exchange": exchange,
        "symbol": symbol,
        "horizon_sessions": 10,
        "model_version": model_version,
    }
    approval = db.query(ModelReleaseApproval).filter_by(**key).one_or_none()
    if approval is None:
        approval = ModelReleaseApproval(**key)
        db.add(approval)
    approval.backtest_report_json = json.dumps(backtest, allow_nan=False)
    approval.paper_track_report_json = json.dumps(paper, allow_nan=False)
    approval.reviewer = reviewer
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    approval.status = "approved"
    for field, value in metrics.items():
        setattr(approval, field, value)
    db.commit()
    db.refresh(approval)
    return approval


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backtest-report", required=True)
    parser.add_argument("--paper-report", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--minimum-paper-samples", required=True, type=int)
    parser.add_argument("--exchange", choices=("NGX",), default="NGX")
    args = parser.parse_args()
    with open(args.backtest_report, encoding="utf-8") as source:
        backtest = json.load(source)
    with open(args.paper_report, encoding="utf-8") as source:
        paper = json.load(source)

    db = SessionLocal()
    try:
        approval = approve_model(
            db,
            backtest=backtest,
            paper=paper,
            exchange=args.exchange,
            symbol=args.symbol,
            model_version=args.model_version,
            reviewer=args.reviewer,
            minimum_paper_samples=args.minimum_paper_samples,
        )
        print(
            f"Approved {approval.exchange} {args.symbol.upper()} {approval.horizon_sessions}-session "
            f"model {approval.model_version}; the API still requires a fresh, current-date signal row."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
