from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CandleRecord(Base):
    __tablename__ = 'market_candles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint('symbol','timeframe','time', name='uq_market_candle'),
        Index('ix_market_candles_lookup','symbol','timeframe','time'),
    )

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False)  # price, rsi, macd, etc
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # up, down, cross_up, cross_down
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default='1h')
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notification_channels: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of channels
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    fired_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_alerts_symbol_enabled', 'symbol', 'enabled'),
        Index('ix_alerts_created_at', 'created_at'),
    )

class AlertHistory(Base):
    __tablename__ = 'alert_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(36), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_value: Mapped[float] = mapped_column(Float, nullable=False)
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notification_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_channels: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index('ix_alert_history_alert_id', 'alert_id'),
        Index('ix_alert_history_fired_at', 'fired_at'),
        Index('ix_alert_history_symbol', 'symbol'),
    )


# ==========================================================
# Phase 15 — Learning & Evaluation Engine
# ==========================================================

class TradingSignal(Base):
    """A recorded analysis decision. Python computes; the LLM only narrates.

    persisted after every directional analyze(); outcomes are resolved
    walk-forward by the OutcomeResolver (never lookahead into the present)."""
    __tablename__ = 'trading_signals'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    strategy_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    indicators_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # long / short
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality: Mapped[str] = mapped_column(String(20), nullable=False, default='live')
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_signals_symbol_tf', 'symbol', 'timeframe'),
        Index('ix_signals_resolved', 'resolved'),
        Index('ix_signals_created_at', 'created_at'),
    )


class SignalOutcome(Base):
    """Deterministic walk-forward resolution of a recorded signal."""
    __tablename__ = 'signal_outcomes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey('trading_signals.id'), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)  # win / loss / breakeven / timeout
    pnl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_favorable: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_adverse: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bars_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_outcomes_signal_id', 'signal_id'),
    )


class StrategyRegistry(Base):
    """Strategies that have been promoted from candidates by human approval."""
    __tablename__ = 'strategy_registry'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='candidate')
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_registry_status', 'status'),
    )


class MarketRegime(Base):
    """Point-in-time regime label per symbol/timeframe (deterministic)."""
    __tablename__ = 'market_regimes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    trend: Mapped[str] = mapped_column(String(10), nullable=False)
    volatility: Mapped[str] = mapped_column(String(10), nullable=False)
    regime_label: Mapped[str] = mapped_column(String(40), nullable=False)  # bullish_trending_high_vol
    indicators: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_regime_symbol_tf', 'symbol', 'timeframe'),
        Index('ix_regime_detected_at', 'detected_at'),
    )


class StrategyCandidate(Base):
    """A strategy configuration produced by grid search, awaiting validation/approval."""
    __tablename__ = 'strategy_candidates'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey('strategy_registry.id'), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    backtest_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    walk_forward_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    oos_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='discovered')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_candidates_status', 'status'),
    )


class TrainingRun(Base):
    """A completed ML training run with its deterministic metrics."""
    __tablename__ = 'training_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_type: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    feature_importance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_training_runs_model_type', 'model_type'),
    )


class UserFeedback(Base):
    """Human feedback on past signals — the closed-loop human signal."""
    __tablename__ = 'user_feedback'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey('trading_signals.id'), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)  # thumbs_up / thumbs_down / note
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_user_feedback_signal_id', 'signal_id'),
    )


class PaperTrade(Base):
    """A paper (virtual) position mirrored from a promoted registry strategy."""
    __tablename__ = 'paper_trades'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    target: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default='open')
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_paper_trades_status', 'status'),
    )
