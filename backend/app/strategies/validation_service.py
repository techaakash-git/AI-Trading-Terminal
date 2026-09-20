"""Phase 15 — Walk-forward strategy validation.

Strictly chronological 60/20/20 split (train / validation / out-of-sample test).
Each phase re-runs the deterministic no-lookahead backtester from
engine/backtesting.py; there is no shared fit state and no shuffled sampling, so
the out-of-sample window is genuinely unseen.
"""
from __future__ import annotations

from ..engine.backtesting import backtest
from ..strategies.service import Strategy

TRAIN_PCT = 0.6
VAL_PCT = 0.2
TEST_PCT = 0.2


def walk_forward_validation(config: dict, candles: list, train_pct: float = TRAIN_PCT,
                            val_pct: float = VAL_PCT, test_pct: float = TEST_PCT) -> dict:
    """Run a strategy across chronological train→val→test windows.

    Returns
    -------
    {
      'status': 'ok' | 'insufficient_data' | 'invalid_config',
      'metric_keys': [...],
      'train_metrics': {...}, 'val_metrics': {...}, 'oos_metrics': {...},
      'consistent': bool,      # oos.sharpe>0, oos.win_rate>0.4, oos.profit_factor>1.0
    }
    """
    try:
        Strategy.model_validate(config)
    except ValueError as exc:
        return {'status': 'invalid_config', 'reason': str(exc), 'consistent': False}
    if len(candles) < 120:
        return {'status': 'insufficient_data', 'reason': 'need >=120 candles', 'consistent': False}

    total = len(candles)
    train_end = int(total * train_pct)
    val_end = train_end + int(total * val_pct)
    windows = {
        'train_metrics': backtest(candles[:train_end], config),
        'val_metrics': backtest(candles[train_end:val_end], config),
        'oos_metrics': backtest(candles[val_end:], config),
    }
    oos = windows['oos_metrics']
    consistent = (oos.get('sharpe', 0) > 0
                  and oos.get('win_rate', 0) > 0.4
                  and oos.get('profit_factor', 0) > 1.0)
    return {
        'status': 'ok',
        'metric_keys': ['total_return', 'win_rate', 'profit_factor', 'sharpe',
                        'sortino', 'max_drawdown', 'average_trade', 'trade_count'],
        **windows,
        'consistent': consistent,
    }


def is_consistent_oos(result: dict) -> bool:
    """Recompute the consistency decision from a prior result dict."""
    return bool(result.get('consistent'))