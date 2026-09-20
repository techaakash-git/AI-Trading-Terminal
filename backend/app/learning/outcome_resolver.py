"""Phase 15 — Walk-forward outcome resolution.

`evaluate_outcome` is the deterministic, no-lookahead heart: given a recorded
signal and the candles that arrived strictly after its entry, it walks forward
bar-by-bar and classifies the trade as win / loss / breakeven / timeout.

`OutcomeResolver` is the background task that feeds `evaluate_outcome` from the
market feed on a fixed cadence. It never reaches for future data: it fetches
only historical candles up to now, filtered to bars after the signal time.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TradingSignal, SignalOutcome

logger = logging.getLogger(__name__)

MAX_BARS = 500
RESOLVE_INTERVAL_S = 60


def evaluate_outcome(
    direction: str,
    entry_price: float,
    stop_loss: float | None,
    target: float | None,
    candles: list,
) -> dict:
    """Walk forward through post-entry candles; classify the trade.

    Parameters mirror a recorded signal (no Signal object needed), so the
    function is pure and trivially testable.

    Returns
    -------
    {
        'outcome': 'win' | 'loss' | 'breakeven' | 'timeout',
        'pnl_pct': float,          # %, direction-adjusted
        'max_favorable': float,    # % (MFE)
        'max_adverse': float,      # % (MAE)
        'bars_held': int,
        'exit_price': float,
    }
    """
    if not candles or entry_price <= 0:
        return {'outcome': 'timeout', 'pnl_pct': 0.0, 'max_favorable': 0.0,
                'max_adverse': 0.0, 'bars_held': 0, 'exit_price': entry_price}

    is_long = direction == 'long'
    mfe_pct = 0.0
    mae_pct = 0.0
    exit_index = len(candles) - 1
    exit_price = candles[-1].close
    exit_reason = 'timeout'

    for j, c in enumerate(candles):
        # Favorable/adverse excursion in %, direction-adjusted.
        fav = ((c.high - entry_price) / entry_price * 100.0) if is_long else ((entry_price - c.low) / entry_price * 100.0)
        adv = ((entry_price - c.low) / entry_price * 100.0) if is_long else ((c.high - entry_price) / entry_price * 100.0)
        mfe_pct = max(mfe_pct, fav)
        mae_pct = max(mae_pct, adv)

        # Exit barriers only exist for directional signals.
        if stop_loss is not None and target is not None:
            hit_stop = (c.low <= stop_loss) if is_long else (c.high >= stop_loss)
            hit_target = (c.high >= target) if is_long else (c.low <= target)
            # Conservative tie-break: an OHLC bar touching both resolves as a stop.
            if hit_stop:
                exit_index, exit_price, exit_reason = j, stop_loss, 'stop_loss'
                break
            if hit_target:
                exit_index, exit_price, exit_reason = j, target, 'target'
                break

        if j >= MAX_BARS - 1:
            exit_index, exit_price, exit_reason = j, c.close, 'timeout'
            break

    pnl_pct = ((exit_price - entry_price) / entry_price * 100.0) if is_long else ((entry_price - exit_price) / entry_price * 100.0)
    if exit_reason == 'stop_loss':
        outcome = 'loss'
    elif exit_reason == 'target':
        outcome = 'win'
    elif abs(pnl_pct) < 1e-9:
        outcome = 'breakeven'
    else:
        outcome = 'timeout'

    return {
        'outcome': outcome,
        'pnl_pct': round(pnl_pct, 4),
        'max_favorable': round(mfe_pct, 4),
        'max_adverse': round(mae_pct, 4),
        'bars_held': exit_index + 1,
        'exit_price': exit_price,
    }


class OutcomeResolver:
    """Background task: resolve unresolved signals against post-entry candles.

    Follows the AlertProcessor pattern (start/stop lifecycle wired into the
    FastAPI lifespan) but is deliberately DB-thin — the heavy lifting lives in
    `evaluate_outcome`, which is a pure function.
    """

    def __init__(self, interval_s: int = RESOLVE_INTERVAL_S):
        self.interval_s = interval_s
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self, get_session, get_candles_fn) -> None:
        """get_session -> AsyncSession factory; get_candles_fn(symbol, tf, limit)."""
        self._get_session = get_session
        self._get_candles = get_candles_fn
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._resolve_once()
            except Exception:  # never kill the loop on a transient DB/feed error
                logger.warning('outcome_resolver pass failed', exc_info=True)
            await asyncio.sleep(self.interval_s)

    async def _resolve_once(self) -> None:
        session: AsyncSession = self._get_session()
        try:
            q = select(TradingSignal).where(TradingSignal.resolved == False)  # noqa: E712
            unresolved = list((await session.execute(q)).scalars().all())
            if not unresolved:
                return
            for signal in unresolved:
                candles = await self._get_candles(signal.symbol, signal.timeframe, 500)
                post_entry = [c for c in candles if c.time > int(signal.created_at.timestamp())] if candle_has_time(candles) else candles
                post_entry = post_entry[:MAX_BARS]
                res = evaluate_outcome(
                    signal.direction, signal.entry_price,
                    signal.stop_loss, signal.target, post_entry,
                )
                # Skip breeds of not-yet-actionable signals (need >=1 post bar).
                if not post_entry:
                    continue
                outcome = SignalOutcome(signal_id=signal.id, **res)
                signal.resolved = True
                session.add(outcome)
                await session.commit()
                logger.info('resolved signal %s -> %s (%.2f%%)', signal.id, res['outcome'], res['pnl_pct'])
        finally:
            await session.close()


def candle_has_time(candles: list) -> bool:
    return bool(candles) and hasattr(candles[0], 'time')