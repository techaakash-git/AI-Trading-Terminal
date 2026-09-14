from __future__ import annotations
from dataclasses import dataclass
import math, statistics
from .indicators import atr, ema

@dataclass
class BacktestResult:
    total_return: float; win_rate: float; profit_factor: float; sharpe: float; sortino: float; max_drawdown: float; average_trade: float; trade_count: int; equity_curve: list; trades: list

def backtest(candles, strategy, initial_capital=10000.0):
    """Deterministic, no-lookahead EMA backtest. A signal at i enters no earlier than i+1."""
    fast, slow = int(strategy.get('fast', 20)), int(strategy.get('slow', 50))
    risk_pct, stop_mult = float(strategy.get('risk_pct', 1)), float(strategy.get('stop_atr_multiple', 2))
    target_rr = float(strategy.get('target_risk_reward', 2))
    closes, highs, lows = [c.close for c in candles], [c.high for c in candles], [c.low for c in candles]
    ef, es, atr_values = ema(closes, fast), ema(closes, slow), atr(highs, lows, closes, 14)
    equity, curve, trades, next_free = initial_capital, [initial_capital], [], max(fast, slow)
    for signal_index in range(max(fast, slow), len(candles) - 1):
        if signal_index < next_free or None in (ef[signal_index], es[signal_index], ef[signal_index - 1], es[signal_index - 1], atr_values[signal_index]):
            curve.append(equity); continue
        side = 1 if ef[signal_index] > es[signal_index] and ef[signal_index - 1] <= es[signal_index - 1] else -1 if ef[signal_index] < es[signal_index] and ef[signal_index - 1] >= es[signal_index - 1] else 0
        if not side: curve.append(equity); continue
        entry_index, entry, distance = signal_index + 1, candles[signal_index + 1].open, atr_values[signal_index] * stop_mult
        stop, target = (entry - distance, entry + distance * target_rr) if side == 1 else (entry + distance, entry - distance * target_rr)
        exit_index, exit_price, reason = len(candles) - 1, candles[-1].close, 'end_of_data'
        for j in range(entry_index, len(candles)):
            candle = candles[j]
            # Conservative order when both barriers are touched in an OHLC bar is stop first.
            hit_stop = candle.low <= stop if side == 1 else candle.high >= stop
            hit_target = candle.high >= target if side == 1 else candle.low <= target
            if hit_stop or hit_target:
                exit_index, exit_price, reason = j, (stop if hit_stop else target), ('stop_loss' if hit_stop else 'target')
                break
        return_pct = side * (exit_price - entry) / entry
        position_value = equity * (risk_pct / 100) / max(distance / entry, 1e-12)
        pnl = position_value * return_pct; equity += pnl
        trades.append({'signal_index': signal_index, 'entry_index': entry_index, 'exit_index': exit_index, 'side': 'long' if side == 1 else 'short', 'entry': entry, 'stop_loss': stop, 'target': target, 'exit': exit_price, 'exit_reason': reason, 'pnl': pnl, 'return_pct': return_pct * 100})
        curve.extend([equity] * max(1, exit_index - signal_index)); next_free = exit_index + 1
    returns = [trade['pnl'] / initial_capital for trade in trades]; wins, losses = [x for x in returns if x > 0], [x for x in returns if x < 0]
    avg = sum(returns) / len(returns) if returns else 0; std = statistics.pstdev(returns) if len(returns) > 1 else 0
    downside = [min(item, 0) for item in returns]; dstd = statistics.pstdev(downside) if len(downside) > 1 else 0
    peak, drawdown = initial_capital, 0
    for value in curve: peak, drawdown = max(peak, value), min(drawdown, (value - peak) / peak)
    # Profit factor is unbounded when there are wins but zero losses; cap it to a
    # large finite value so it stays JSON-serializable (json cannot encode inf).
    PROFIT_FACTOR_CAP = 1e9
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (PROFIT_FACTOR_CAP if wins else 0)
    return BacktestResult((equity / initial_capital - 1) * 100, len(wins) / len(returns) * 100 if returns else 0, profit_factor, avg / std * math.sqrt(len(returns)) if std else 0, avg / dstd * math.sqrt(len(returns)) if dstd else 0, abs(drawdown) * 100, avg * 100, len(trades), curve, trades).__dict__
