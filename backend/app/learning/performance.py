"""Phase 15 — Aggregate performance from resolved outcomes.

Pure SQL aggregation over the (signal, outcome) tables. Every figure is computed
from stored, walk-forward results — never from the LLM and never forecast.
"""
from __future__ import annotations

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TradingSignal, SignalOutcome


async def aggregate_performance(db: AsyncSession, symbol: str | None = None,
                                timeframe: str | None = None) -> dict:
    """Summary metrics over resolved outcomes, optionally filtered per symbol.

    Returns
    -------
    {
      'total_signals', 'resolved', 'wins', 'losses', 'breakevens', 'timeouts',
      'win_rate', 'profit_factor', 'expectancy', 'avg_win', 'avg_loss',
      'total_pnl_pct', 'max_drawdown', 'avg_mfe', 'avg_mae',
    }
    """
    sig_q = select(TradingSignal)
    out_q = select(SignalOutcome).join(TradingSignal, SignalOutcome.signal_id == TradingSignal.id)
    if symbol:
        sym = symbol.upper()
        sig_q = sig_q.where(TradingSignal.symbol == sym)
        out_q = out_q.where(TradingSignal.symbol == sym)
    if timeframe:
        sig_q = sig_q.where(TradingSignal.timeframe == timeframe)
        out_q = out_q.where(TradingSignal.timeframe == timeframe)

    signals = list((await db.execute(sig_q)).scalars().all())
    outcomes = list((await db.execute(out_q)).scalars().all())

    total_signals = len(signals)
    resolved = len(outcomes)
    wins = [o for o in outcomes if o.outcome == 'win']
    losses = [o for o in outcomes if o.outcome == 'loss']
    breakevens = sum(1 for o in outcomes if o.outcome == 'breakeven')
    timeouts = sum(1 for o in outcomes if o.outcome == 'timeout')

    win_pcts = [o.pnl_pct for o in wins]
    loss_pcts = [o.pnl_pct for o in losses]
    win_rate = len(wins) / resolved * 100.0 if resolved else 0.0
    gross_win = sum(win_pcts)
    gross_loss = abs(sum(loss_pcts))
    profit_factor = (gross_win / gross_loss) if gross_loss else (1e9 if gross_win else 0.0)
    expectancy = (sum(o.pnl_pct for o in outcomes) / resolved) if resolved else 0.0

    # Drawdown: cumulative equity path from per-outcome PnL (chronological).
    path = [o.resolved_at for o in outcomes]
    pnl_by_time = sorted(outcomes, key=lambda o: (o.resolved_at, o.id))
    running, peak, max_dd = 0.0, 0.0, 0.0
    for o in pnl_by_time:
        running += o.pnl_pct
        peak = max(peak, running)
        max_dd = min(max_dd, running - peak)

    mfe = [o.max_favorable for o in outcomes]
    mae = [o.max_adverse for o in outcomes]
    return {
        'total_signals': total_signals,
        'resolved': resolved,
        'wins': len(wins),
        'losses': len(losses),
        'breakevens': breakevens,
        'timeouts': timeouts,
        'win_rate': round(win_rate, 4),
        'profit_factor': round(min(profit_factor, 1e9), 4),
        'expectancy': round(expectancy, 4),
        'avg_win': round((sum(win_pcts) / len(win_pcts)) if win_pcts else 0.0, 4),
        'avg_loss': round((sum(loss_pcts) / len(loss_pcts)) if loss_pcts else 0.0, 4),
        'total_pnl_pct': round(sum(o.pnl_pct for o in outcomes), 4),
        'max_drawdown': round(abs(max_dd), 4),
        'avg_mfe': round((sum(mfe) / len(mfe)) if mfe else 0.0, 4),
        'avg_mae': round((sum(mae) / len(mae)) if mae else 0.0, 4),
    }


async def performance_by_symbol(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Per-symbol aggregate breakdown for the performance tab."""
    rows = (await db.execute(
        select(TradingSignal.symbol, TradingSignal.timeframe)
        .distinct()
    )).all()
    out = []
    for symbol, timeframe in rows[:limit]:
        stats = await aggregate_performance(db, symbol=str(symbol), timeframe=str(timeframe))
        out.append({**stats, 'symbol': symbol, 'timeframe': timeframe})
    return out