"""Typed public response contracts for market research endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SignalHorizon(BaseModel):
    unit: str = "trading_days"
    min: int = 5
    max: int = 20
    primary: int = 10


class SignalValidation(BaseModel):
    model_version: Optional[str] = None
    status: Optional[str] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    paper_samples: Optional[int] = None
    paper_hit_rate: Optional[float] = None
    paper_brier_score: Optional[float] = None
    paper_prior_baseline_brier_score: Optional[float] = None
    paper_mean_net_directional_return_pct: Optional[float] = None
    backtest_brier_score: Optional[float] = None
    backtest_prior_baseline_brier_score: Optional[float] = None
    backtest_mean_net_excess_vs_matched_benchmark_pct: Optional[float] = None


class ResearchSignal(BaseModel):
    available: bool
    status: str
    direction: Optional[str] = None
    horizon: SignalHorizon
    probability_positive: Optional[float] = None
    expected_return_pct: Optional[float] = None
    as_of: Optional[datetime] = None
    evidence: list[Any] = Field(default_factory=list)
    validation: Optional[SignalValidation] = None


class MarketSummaryRow(BaseModel):
    symbol: str
    name: str
    market_cap: Optional[str] = None
    price: float
    change_pct: float
    currency: str
    exchange: str
    as_of: datetime
    source: str
    stale: bool


class MarketSummaryMeta(BaseModel):
    data_available: bool
    reason: Optional[str] = None
    exchange: str
    as_of: Optional[datetime] = None
    stale: bool


class MarketSummaryResponse(BaseModel):
    status: str
    data: list[MarketSummaryRow]
    meta: MarketSummaryMeta


class MarketBar(BaseModel):
    date: str
    exchange: str
    symbol: str
    currency: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None
    source: str
    as_of: datetime
    stale: bool
    verified: bool


class ForecastMeta(BaseModel):
    data_available: bool
    exchange: str
    symbol: str
    currency: str
    as_of: Optional[datetime] = None
    source: Optional[str] = None
    stale: bool


class ForecastResponse(BaseModel):
    status: str
    data: list[MarketBar]
    meta: ForecastMeta
    signal: ResearchSignal


class InsightData(BaseModel):
    ticker: str
    exchange: str
    currency: str
    price: Optional[float] = None
    data_as_of: Optional[datetime] = None
    data_source: Optional[str] = None
    data_stale: bool
    recommendation: Optional[str] = None
    signal: ResearchSignal
    ai_confidence: Optional[float] = None
    market_stability: Optional[float] = None
    public_sentiment: Optional[float] = None
    safety_index: Optional[float] = None
    rsi_impact: Optional[float] = None
    ema_impact: Optional[float] = None
    evidence: list[Any] = Field(default_factory=list)
    explanation: str


class InsightsResponse(BaseModel):
    status: str
    data: InsightData
