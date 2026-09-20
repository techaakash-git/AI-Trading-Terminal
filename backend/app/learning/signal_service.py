"""Phase 15 — Signal recording & querying.

Persists a trading signal whenever the analysis engine produced a directional
decision (long/short). All numerics come from risk.py / indicators.py — this
module only stores what Python already computed; it never infers anything.
"""
from __future__ import annotations

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TradingSignal, SignalOutcome
from ..schemas.learning import SignalCreate


async def record_signal(db: AsyncSession, payload: SignalCreate) -> TradingSignal:
    """Persist a directional signal. No calculations here — config/snapshot and
    prices are passed through as computed by the deterministic engine."""
    signal = TradingSignal(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        strategy_config=payload.strategy_config,
        indicators_snapshot=payload.indicators_snapshot,
        direction=payload.direction,
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        target=payload.target,
        data_quality=payload.data_quality,
        resolved=False,
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)
    return signal


async def get_signals(
    db: AsyncSession,
    symbol: str | None = None,
    timeframe: str | None = None,
    resolved: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TradingSignal]:
    """Query signals with optional filters, newest first."""
    q = select(TradingSignal).order_by(desc(TradingSignal.created_at))
    if symbol:
        q = q.where(TradingSignal.symbol == symbol.upper())
    if timeframe:
        q = q.where(TradingSignal.timeframe == timeframe)
    if resolved is not None:
        q = q.where(TradingSignal.resolved == resolved)
    q = q.limit(min(max(limit, 1), 500)).offset(max(offset, 0))
    return list((await db.execute(q)).scalars().all())


async def get_signals_count(db: AsyncSession, resolved: bool | None = None) -> int:
    q = select(func.count()).select_from(TradingSignal)
    if resolved is not None:
        q = q.where(TradingSignal.resolved == resolved)
    return (await db.execute(q)).scalar() or 0


async def get_signal(db: AsyncSession, signal_id: int) -> TradingSignal | None:
    return await db.get(TradingSignal, signal_id)


async def get_outcomes(
    db: AsyncSession,
    signal_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SignalOutcome]:
    """Query resolved outcomes, newest first."""
    q = select(SignalOutcome).order_by(desc(SignalOutcome.resolved_at))
    if signal_id is not None:
        q = q.where(SignalOutcome.signal_id == signal_id)
    q = q.limit(min(max(limit, 1), 500)).offset(max(offset, 0))
    return list((await db.execute(q)).scalars().all())


async def get_signal_with_outcome(db: AsyncSession, signal_id: int) -> dict:
    """A signal paired with its outcome (or None)."""
    signal = await get_signal(db, signal_id)
    if not signal:
        return {}
    outcomes = await get_outcomes(db, signal_id=signal_id, limit=1)
    return {'signal': signal, 'outcome': outcomes[0] if outcomes else None}