"""Pydantic I/O schemas for the Learning & Evaluation Engine (Phase 15).

These mirror the SQLAlchemy models but only expose fields that the HTTP layer
and frontend need. Validation here is structural only — every numeric value is
produced by the deterministic engine layer beforehand.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SignalCreate(BaseModel):
    """A signal recorded after a directional analysis. Numerics come from
    risk.py / indicators.py — never from the LLM."""
    model_config = ConfigDict(from_attributes=True)

    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=8)
    strategy_config: dict
    indicators_snapshot: dict
    direction: str = Field(pattern='^(long|short)$')
    entry_price: float = Field(gt=0)
    stop_loss: float | None = None
    target: float | None = None
    data_quality: str = Field(default='live', pattern='^(live|degraded)$')


class OutcomeUpdate(BaseModel):
    """Resolved walk-forward outcome for a signal."""
    model_config = ConfigDict(from_attributes=True)

    outcome: str = Field(pattern='^(win|loss|breakeven|timeout)$')
    pnl_pct: float
    max_favorable: float = 0.0
    max_adverse: float = 0.0
    bars_held: int = Field(default=0, ge=0)
    exit_price: float


class CandidateCreate(BaseModel):
    """A strategy candidate discovered via grid search (valid Strategy config)."""
    model_config = ConfigDict(from_attributes=True)

    config: dict
    parent_id: int | None = None


class CandidatePromote(BaseModel):
    """Human-approval promotion payload for a candidate."""
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=100)


class StrategyStatusUpdate(BaseModel):
    """Update a registered strategy's lifecycle status."""
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(pattern='^(active|paused|archived|candidate)$')


class FeedbackCreate(BaseModel):
    """Human feedback on a signal."""
    model_config = ConfigDict(from_attributes=True)

    signal_id: int | None = None
    feedback_type: str = Field(pattern='^(thumbs_up|thumbs_down|note)$')
    note: str | None = None


class TrainRequest(BaseModel):
    """Trigger an ML training run. model_type and optional symbol scope."""
    model_config = ConfigDict(from_attributes=True)

    model_type: str = Field(pattern='^(classifier|expectancy|regime)$')
    symbol: str | None = Field(default=None, max_length=32)


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    symbol: str
    timeframe: str
    strategy_config: dict
    indicators_snapshot: dict
    direction: str
    entry_price: float
    stop_loss: float | None
    target: float | None
    data_quality: str
    resolved: bool
    created_at: datetime


class OutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    signal_id: int
    outcome: str
    pnl_pct: float
    max_favorable: float
    max_adverse: float
    bars_held: int
    exit_price: float
    resolved_at: datetime


class RegimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    symbol: str
    timeframe: str
    trend: str
    volatility: str
    regime_label: str
    indicators: dict
    detected_at: datetime


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parent_id: int | None
    config: dict
    backtest_metrics: dict
    walk_forward_metrics: dict
    oos_metrics: dict
    status: str
    created_at: datetime


class RegistryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    version: int
    config: dict
    status: str
    win_rate: float | None
    profit_factor: float | None
    sharpe: float | None
    max_drawdown: float | None
    trade_count: int
    created_at: datetime


class TrainingRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    model_type: str
    symbol: str | None
    metrics: dict
    feature_importance: dict | None
    sample_count: int
    created_at: datetime


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    signal_id: int | None
    feedback_type: str
    note: str | None
    created_at: datetime