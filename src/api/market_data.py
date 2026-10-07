"""Read-only market-data queries and response serialization."""

import os
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from src.api.database import MarketDailyBar, ModelReleaseApproval, PaperSignal
from src.data import investo_provider

NGX_TIMEZONE = ZoneInfo("Africa/Lagos")
STALE_AFTER_DAYS = 4


def market_data_enabled() -> bool:
    """Whether an authorized market-data source is configured."""
    if investo_provider.is_configured():
        return True
    return (
        bool(os.getenv("NGX_DATA_API_TOKEN", "").strip())
        and os.getenv("NGX_MARKET_DATA_USE_APPROVED", "false").strip().lower() == "true"
    )


def market_data_source() -> str | None:
    if investo_provider.is_configured():
        return investo_provider.SOURCE_NAME
    if (
        os.getenv("NGX_DATA_API_TOKEN", "").strip()
        and os.getenv("NGX_MARKET_DATA_USE_APPROVED", "false").strip().lower() == "true"
    ):
        return "NGX Market Data API"
    return None


def _provider_bar_as_object(record: dict) -> SimpleNamespace:
    return SimpleNamespace(**record)


def is_stale(trade_date: date, now: datetime | None = None) -> bool:
    current_date = (now or datetime.now(NGX_TIMEZONE)).date()
    return current_date - trade_date > timedelta(days=STALE_AFTER_DAYS)


def latest_bar(db: Session, symbol: str, exchange: str = "NGX") -> MarketDailyBar | None:
    if investo_provider.is_configured() and exchange.upper() == "NGX":
        bars = recent_bars(db, symbol, limit=1, exchange=exchange)
        return bars[-1] if bars else None
    return (
        db.query(MarketDailyBar)
        .filter(
            MarketDailyBar.exchange == exchange.upper(),
            MarketDailyBar.symbol == symbol.upper(),
            MarketDailyBar.provider_verified.is_(True),
        )
        .order_by(MarketDailyBar.trade_date.desc())
        .first()
    )


def recent_bars(
    db: Session, symbol: str, limit: int = 120, exchange: str = "NGX"
) -> list[MarketDailyBar]:
    if investo_provider.is_configured() and exchange.upper() == "NGX":
        lookback_days = max(60, limit * 3)
        start_date = datetime.now(NGX_TIMEZONE).date() - timedelta(days=lookback_days)
        bars = investo_provider.fetch_history(symbol, start_date)
        return [_provider_bar_as_object(bar) for bar in bars[-limit:]]
    rows = (
        db.query(MarketDailyBar)
        .filter(
            MarketDailyBar.exchange == exchange.upper(),
            MarketDailyBar.symbol == symbol.upper(),
            MarketDailyBar.provider_verified.is_(True),
        )
        .order_by(MarketDailyBar.trade_date.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def bar_as_dict(bar: MarketDailyBar, stale: bool | None = None) -> dict:
    return {
        "date": bar.trade_date.isoformat(),
        "exchange": bar.exchange,
        "symbol": bar.symbol,
        "currency": bar.currency,
        "open": float(bar.open) if bar.open is not None else None,
        "high": float(bar.high) if bar.high is not None else None,
        "low": float(bar.low) if bar.low is not None else None,
        "close": float(bar.close),
        "volume": float(bar.volume) if bar.volume is not None else None,
        "source": bar.source,
        "as_of": bar.source_as_of.isoformat(),
        "stale": is_stale(bar.trade_date) if stale is None else stale,
        "verified": bool(bar.provider_verified),
    }


def market_summary(db: Session, exchange: str = "NGX") -> dict:
    if not market_data_enabled():
        return {
            "status": "success",
            "data": [],
            "meta": {
                "data_available": False,
                "reason": "market_data_not_configured",
                "exchange": exchange,
                "as_of": None,
                "stale": True,
            },
        }

    if investo_provider.is_configured():
        stocks, meta = investo_provider.fetch_stocks()
        rows = []
        for stock in stocks:
            trade_date = stock["trade_date"]
            rows.append(
                {
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "market_cap": (
                        str(stock["market_cap"]) if stock["market_cap"] is not None else None
                    ),
                    "price": stock["price"],
                    "change_pct": stock["change_pct"],
                    "currency": "NGN",
                    "exchange": "NGX",
                    "as_of": stock["as_of"].isoformat(),
                    "source": investo_provider.SOURCE_NAME,
                    "stale": is_stale(trade_date),
                }
            )
        rows.sort(key=lambda row: row["symbol"])
        latest_as_of = max((row["as_of"] for row in rows), default=None)
        return {
            "status": "success",
            "data": rows,
            "meta": {
                "data_available": bool(rows),
                "reason": None if rows else "no_market_data",
                "exchange": "NGX",
                "as_of": meta.get("generated_at") or latest_as_of,
                "stale": bool(rows) and all(row["stale"] for row in rows),
            },
        }

    symbols = (
        db.query(MarketDailyBar.symbol)
        .filter(
            MarketDailyBar.exchange == exchange.upper(),
            MarketDailyBar.provider_verified.is_(True),
        )
        .distinct()
        .all()
    )
    rows = []
    for (symbol,) in symbols:
        bars = recent_bars(db, symbol, limit=2, exchange=exchange)
        if not bars:
            continue
        current = bars[-1]
        previous = bars[-2] if len(bars) > 1 else current
        current_close = float(current.close)
        previous_close = float(previous.close)
        change = (
            ((current_close - previous_close) / previous_close) * 100
            if previous_close
            else 0.0
        )
        rows.append(
            {
                "symbol": current.symbol,
                "name": current.symbol,
                "market_cap": None,
                "price": current_close,
                "change_pct": change,
                "currency": current.currency,
                "exchange": current.exchange,
                "as_of": current.source_as_of.isoformat(),
                "source": current.source,
                "stale": is_stale(current.trade_date),
            }
        )
    rows.sort(key=lambda row: row["symbol"])
    as_of = max((row["as_of"] for row in rows), default=None)
    return {
        "status": "success",
        "data": rows,
        "meta": {
            "data_available": bool(rows),
            "reason": None if rows else "no_market_data",
            "exchange": exchange.upper(),
            "as_of": as_of,
            "stale": bool(rows) and all(row["stale"] for row in rows),
        },
    }


def release_approval(
    db: Session, signal: PaperSignal | None
) -> ModelReleaseApproval | None:
    if signal is None:
        return None
    return (
        db.query(ModelReleaseApproval)
        .filter(
            ModelReleaseApproval.exchange == signal.exchange,
            ModelReleaseApproval.symbol == signal.symbol,
            ModelReleaseApproval.horizon_sessions == signal.horizon_sessions,
            ModelReleaseApproval.model_version == signal.model_version,
            ModelReleaseApproval.status == "approved",
        )
        .first()
    )


def published_signal(
    db: Session,
    symbol: str,
    exchange: str = "NGX",
    current_bar: MarketDailyBar | None = None,
) -> PaperSignal | None:
    if current_bar is None:
        # Callers pass the latest verified close. Matching that exact session
        # prevents old, manually relabeled rows resurfacing as current signals.
        return None
    signal = (
        db.query(PaperSignal)
        .filter(
            PaperSignal.exchange == exchange.upper(),
            PaperSignal.symbol == symbol.upper(),
            PaperSignal.horizon_sessions == 10,
            PaperSignal.validation_status == "published",
            PaperSignal.signal_date == current_bar.trade_date,
        )
        .order_by(PaperSignal.signal_date.desc())
        .first()
    )
    return signal if release_approval(db, signal) is not None else None


def signal_as_dict(
    signal: PaperSignal | None,
    current_bar: MarketDailyBar | None,
    approval: ModelReleaseApproval | None = None,
) -> dict:
    if (
        signal is None
        or current_bar is None
        or approval is None
        or is_stale(current_bar.trade_date)
    ):
        return {
            "available": False,
            "status": (
                "stale_data"
                if current_bar is not None and is_stale(current_bar.trade_date)
                else "not_validated"
            ),
            "direction": None,
            "horizon": {"unit": "trading_days", "min": 5, "max": 20, "primary": 10},
            "as_of": current_bar.source_as_of.isoformat() if current_bar else None,
            "evidence": [],
            "validation": None,
        }
    try:
        import json

        evidence = json.loads(signal.evidence_json or "[]")
        if not isinstance(evidence, list):
            evidence = []
    except (TypeError, ValueError):
        evidence = []
    validation = None
    if approval is not None:
        validation = {
            "model_version": signal.model_version,
            "status": approval.status,
            "reviewer": approval.reviewer,
            "reviewed_at": approval.reviewed_at.isoformat(),
            "paper_samples": approval.paper_sample_count,
            "paper_hit_rate": float(approval.paper_hit_rate),
            "paper_brier_score": float(approval.paper_brier_score),
            "paper_prior_baseline_brier_score": float(approval.paper_prior_baseline_brier_score),
            "paper_mean_net_directional_return_pct": float(approval.paper_mean_net_directional_return_pct),
            "backtest_brier_score": float(approval.backtest_brier_score),
            "backtest_prior_baseline_brier_score": float(approval.backtest_prior_baseline_brier_score),
            "backtest_mean_net_excess_vs_matched_benchmark_pct": float(
                approval.backtest_mean_net_excess_vs_matched_benchmark_pct
            ),
        }
    return {
        "available": True,
        "status": "published",
        "direction": signal.direction,
        "horizon": {
            "unit": "trading_days",
            "min": 5,
            "max": 20,
            "primary": signal.horizon_sessions,
        },
        "probability_positive": (
            float(signal.probability_positive)
            if signal.probability_positive is not None
            else None
        ),
        "expected_return_pct": (
            float(signal.expected_return_pct)
            if signal.expected_return_pct is not None
            else None
        ),
        "as_of": signal.source_as_of.isoformat() if signal.source_as_of else None,
        "evidence": evidence,
        "validation": validation,
    }
