"""Phase 15 — market regime persistence.

The deterministic label comes from engine/regimes.detect_regime (Python computes).
This service only stores / queries those labels per symbol+timeframe.
"""
from __future__ import annotations

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import MarketRegime


async def record_regime(db: AsyncSession, payload: dict) -> MarketRegime:
    """Persist a detected regime snapshot."""
    row = MarketRegime(
        symbol=payload['symbol'].upper(),
        timeframe=payload['timeframe'],
        trend=payload['trend'],
        volatility=payload['volatility'],
        regime_label=payload['regime_label'],
        indicators=payload.get('indicators', {}),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def latest_regime(db: AsyncSession, symbol: str, timeframe: str) -> MarketRegime | None:
    q = (select(MarketRegime)
         .where(MarketRegime.symbol == symbol.upper(), MarketRegime.timeframe == timeframe)
         .order_by(desc(MarketRegime.detected_at)).limit(1))
    return (await db.execute(q)).scalars().first()


async def regime_history(db: AsyncSession, symbol: str | None, timeframe: str | None,
                         limit: int = 100) -> list[MarketRegime]:
    q = select(MarketRegime).order_by(desc(MarketRegime.detected_at))
    if symbol:
        q = q.where(MarketRegime.symbol == symbol.upper())
    if timeframe:
        q = q.where(MarketRegime.timeframe == timeframe)
    q = q.limit(min(max(limit, 1), 500))
    return list((await db.execute(q)).scalars().all())