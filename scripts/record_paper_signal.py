"""Record an explicitly paper-only 5/10/20-session research prediction."""

import argparse
import json
from decimal import Decimal

from src.api.database import PaperSignal, SessionLocal
from src.api.market_data import is_stale, latest_bar, market_data_enabled


def record_paper_signal(
    db,
    *,
    symbol: str,
    direction: str,
    probability_positive: float,
    model_version: str,
    evidence: str,
    horizon_sessions: int = 10,
    prior_probability_positive: float | None = None,
) -> PaperSignal:
    if not market_data_enabled():
        raise ValueError("Market-data use is not configured and approved")
    symbol = symbol.strip().upper()
    direction = direction.strip().lower()
    if direction not in {"positive", "negative"}:
        raise ValueError("direction must be positive or negative")
    if horizon_sessions not in {5, 10, 20}:
        raise ValueError("horizon_sessions must be 5, 10, or 20")
    if not 0 <= probability_positive <= 1:
        raise ValueError("probability_positive must be between 0 and 1")
    if prior_probability_positive is not None and not 0 <= prior_probability_positive <= 1:
        raise ValueError("prior_probability_positive must be between 0 and 1")
    if (direction == "positive" and probability_positive <= 0.5) or (
        direction == "negative" and probability_positive >= 0.5
    ):
        raise ValueError("direction must agree with probability_positive")
    model_version = model_version.strip()
    evidence = evidence.strip()
    if not symbol or not model_version or not evidence:
        raise ValueError("symbol, model_version, and evidence are required")

    bar = latest_bar(db, symbol)
    if bar is None or is_stale(bar.trade_date):
        raise ValueError("A fresh, verified NGX close is required to start paper tracking")
    duplicate = (
        db.query(PaperSignal)
        .filter_by(
            exchange=bar.exchange,
            symbol=symbol,
            signal_date=bar.trade_date,
            horizon_sessions=horizon_sessions,
            model_version=model_version,
        )
        .first()
    )
    if duplicate is not None:
        raise ValueError("This model already has a paper signal for that symbol and close")

    signal = PaperSignal(
        exchange=bar.exchange,
        symbol=symbol,
        signal_date=bar.trade_date,
        horizon_sessions=horizon_sessions,
        direction=direction,
        probability_positive=Decimal(str(probability_positive)),
        prior_probability_positive=(
            Decimal(str(prior_probability_positive))
            if prior_probability_positive is not None
            else None
        ),
        model_version=model_version,
        validation_status="paper",
        evidence_json=json.dumps([evidence]),
        source_as_of=bar.source_as_of,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--direction", required=True, choices=("positive", "negative"))
    parser.add_argument("--probability-positive", required=True, type=float)
    parser.add_argument(
        "--prior-probability-positive",
        type=float,
        help="training-only prior probability captured at prediction time; required for release validation",
    )
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--evidence", required=True, help="brief explanation of the paper prediction")
    parser.add_argument("--horizon", type=int, choices=(5, 10, 20), default=10)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        signal = record_paper_signal(
            db,
            symbol=args.symbol,
            direction=args.direction,
            probability_positive=args.probability_positive,
            prior_probability_positive=args.prior_probability_positive,
            model_version=args.model_version,
            evidence=args.evidence,
            horizon_sessions=args.horizon,
        )
        print(f"Recorded {signal.symbol} as paper-only for {signal.horizon_sessions} trading days.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
