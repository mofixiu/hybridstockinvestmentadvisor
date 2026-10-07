"""SQLAlchemy models and session setup for HybStockAdvisor."""

import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set before starting the API")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    risk_tolerance = Column(String(50), default="Medium")
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(30), nullable=False)
    quantity = Column(Float, nullable=False)
    average_buy_price = Column(Float, nullable=False)
    added_at = Column(DateTime, server_default=func.current_timestamp())


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(30), nullable=False)
    added_at = Column(DateTime, server_default=func.current_timestamp())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False)
    # `otp` is retained for compatibility with existing databases. New reset
    # requests store only a SHA-256 digest in otp_hash.
    otp = Column(String(6), nullable=False)
    otp_hash = Column(String(64), nullable=True)
    failed_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    reset_token = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=False)


class InviteToken(Base):
    __tablename__ = "tester_invites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class MarketDailyBar(Base):
    __tablename__ = "market_daily_bars"
    __table_args__ = (
        UniqueConstraint("exchange", "symbol", "trade_date", name="uq_market_daily_bar"),
        Index("ix_market_bar_lookup", "exchange", "symbol", "trade_date"),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    exchange = Column(String(12), nullable=False, default="NGX")
    symbol = Column(String(30), nullable=False)
    trade_date = Column(Date, nullable=False)
    currency = Column(String(3), nullable=False, default="NGN")
    open = Column(Numeric(20, 6), nullable=True)
    high = Column(Numeric(20, 6), nullable=True)
    low = Column(Numeric(20, 6), nullable=True)
    close = Column(Numeric(20, 6), nullable=False)
    volume = Column(Numeric(24, 4), nullable=True)
    source = Column(String(80), nullable=False)
    source_as_of = Column(DateTime, nullable=False)
    provider_verified = Column(Boolean, nullable=False, default=False)
    ingested_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())


class PaperSignal(Base):
    __tablename__ = "paper_signals"
    __table_args__ = (
        UniqueConstraint(
            "exchange", "symbol", "signal_date", "horizon_sessions", "model_version",
            name="uq_paper_signal_run",
        ),
        Index("ix_paper_signal_lookup", "exchange", "symbol", "signal_date"),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    exchange = Column(String(12), nullable=False)
    symbol = Column(String(30), nullable=False)
    signal_date = Column(Date, nullable=False)
    horizon_sessions = Column(SmallInteger, nullable=False, default=10)
    direction = Column(String(12), nullable=False)
    probability_positive = Column(Numeric(8, 6), nullable=True)
    # Captured when the prediction is made so the paper score never estimates
    # its baseline from the outcomes it is evaluating.
    prior_probability_positive = Column(Numeric(8, 6), nullable=True)
    expected_return_pct = Column(Numeric(12, 6), nullable=True)
    model_version = Column(String(80), nullable=False)
    validation_status = Column(String(20), nullable=False, default="pending")
    evidence_json = Column(Text, nullable=True)
    source_as_of = Column(DateTime, nullable=True)
    realized_return_pct = Column(Numeric(12, 6), nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())


class ModelReleaseApproval(Base):
    __tablename__ = "model_release_approvals"
    __table_args__ = (
        UniqueConstraint(
            "exchange", "symbol", "horizon_sessions", "model_version",
            name="uq_model_release_approval",
        ),
    )

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    exchange = Column(String(12), nullable=False)
    symbol = Column(String(30), nullable=False)
    horizon_sessions = Column(SmallInteger, nullable=False)
    model_version = Column(String(80), nullable=False)
    backtest_report_json = Column(Text, nullable=False)
    paper_track_report_json = Column(Text, nullable=False)
    paper_sample_count = Column(Integer, nullable=False)
    paper_hit_rate = Column(Float, nullable=False)
    paper_brier_score = Column(Float, nullable=False)
    paper_prior_baseline_brier_score = Column(Float, nullable=False)
    paper_mean_net_directional_return_pct = Column(Float, nullable=False)
    backtest_brier_score = Column(Float, nullable=False)
    backtest_prior_baseline_brier_score = Column(Float, nullable=False)
    backtest_mean_net_excess_vs_matched_benchmark_pct = Column(Float, nullable=False)
    reviewer = Column(String(100), nullable=False)
    reviewed_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="approved")


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
