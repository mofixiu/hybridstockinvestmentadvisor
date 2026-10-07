"""Record today's prediction from an already approved 10-session model."""

import argparse
import json
from decimal import Decimal

from src.api.database import PaperSignal, SessionLocal
from src.api.market_data import is_stale, latest_bar, market_data_enabled


def publish_signal(
    db,
    *,
    symbol: str,
    direction: str,
    probability_positive: float,
    model_version: str,
    evidence: str,
) -> PaperSignal:
    if not market_data_enabled():
        raise ValueError("Market-data use is not configured and approved")
    symbol = symbol.strip().upper()
    direction = direction.strip().lower()
    model_version = model_version.strip()
    evidence = evidence.strip()
    if direction not in {"positive", "negative"}:
        raise ValueError("direction must be positive or negative")
    if not 0 <= probability_positive <= 1:
        raise ValueError("probability_positive must be between 0 and 1")
    if (direction == "positive" and probability_positive <= 0.5) or (
        direction == "negative" and probability_positive >= 0.5
    ):
        raise ValueError("direction must agree with probability_positive")
    if not symbol or not model_version or not evidence:
        raise ValueError("symbol, model_version, and evidence are required")
    bar = latest_bar(db, symbol)
    if bar is None or is_stale(bar.trade_date):
        raise ValueError("A fresh, verified NGX close is required to publish a signal")
    approval = release_approval_for(db, symbol, model_version)
    if approval is None:
        raise ValueError("This model has no approved backtest and paper-track release")

    signal = (
        db.query(PaperSignal)
        .filter_by(
            exchange=bar.exchange,
            symbol=symbol,
            signal_date=bar.trade_date,
            horizon_sessions=10,
            model_version=model_version,
        )
        .one_or_none()
    )
    if signal is None:
        signal = PaperSignal(
            exchange=bar.exchange,
            symbol=symbol,
            signal_date=bar.trade_date,
            horizon_sessions=10,
            direction=direction,
            model_version=model_version,
            source_as_of=bar.source_as_of,
        )
        db.add(signal)
    elif signal.validation_status == "published":
        raise ValueError("A published signal already exists for this model and close")

    signal.direction = direction
    signal.probability_positive = Decimal(str(probability_positive))
    signal.validation_status = "published"
    signal.evidence_json = json.dumps([evidence])
    signal.source_as_of = bar.source_as_of
    db.commit()
    db.refresh(signal)
    return signal


def release_approval_for(db, symbol: str, model_version: str):
    from src.api.database import ModelReleaseApproval

    return (
        db.query(ModelReleaseApproval)
        .filter_by(
            exchange="NGX",
            symbol=symbol,
            horizon_sessions=10,
            model_version=model_version,
            status="approved",
        )
        .first()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--direction", required=True, choices=("positive", "negative"))
    parser.add_argument("--probability-positive", required=True, type=float)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        signal = publish_signal(
            db,
            symbol=args.symbol,
            direction=args.direction,
            probability_positive=args.probability_positive,
            model_version=args.model_version,
            evidence=args.evidence,
        )
        print(
            f"Published {signal.symbol} research signal for {signal.horizon_sessions} sessions. "
            "No trade was placed."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
