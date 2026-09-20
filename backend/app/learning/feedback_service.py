"""Phase 15 — user feedback on signals (human-in-the-loop for the learner)."""
from __future__ import annotations

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TradingSignal, UserFeedback


async def create_feedback(db: AsyncSession, payload) -> UserFeedback:
    """Validate the referenced signal exists (when provided), then persist."""
    if payload.signal_id is not None:
        signal = await db.get(TradingSignal, payload.signal_id)
        if signal is None:
            raise ValueError('signal not found')
    row = UserFeedback(signal_id=payload.signal_id,
                       feedback_type=payload.feedback_type,
                       note=payload.note)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_feedback(db: AsyncSession, signal_id: int | None = None,
                        limit: int = 100, offset: int = 0) -> list[UserFeedback]:
    q = select(UserFeedback).order_by(desc(UserFeedback.created_at))
    if signal_id is not None:
        q = q.where(UserFeedback.signal_id == signal_id)
    q = q.limit(min(max(limit, 1), 500)).offset(max(offset, 0))
    return list((await db.execute(q)).scalars().all())