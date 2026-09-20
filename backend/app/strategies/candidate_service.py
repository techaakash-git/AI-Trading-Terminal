"""Phase 15 — Strategy candidate discovery via grid search.

Candidates are plain `Strategy`-compatible config dicts (see strategies/service.py)
produced by enumerating a declared parameter grid. Nothing is generated or
executed as code, and no numeric claim is invented here — every candidate is
validated later by the engine's walk-forward backtester.
"""
from __future__ import annotations

from itertools import product

from ..strategies.service import Strategy


def generate_candidates(base_config: dict, param_grid: dict, limit: int = 200) -> list[dict]:
    """Cartesian product of param_grid entries merged over base_config.

    Parameters
    ----------
    base_config : fixed keys every candidate must carry (e.g. name, risk_pct).
    param_grid   : {param: [values]} — only Strategy fields are honored.
    limit        : hard cap so an accidental huge grid can't explode memory.

    Returns
    -------
    A list of valid Strategy config dicts (invalid combos like fast >= slow
    are skipped, never raised).
    """
    valid = set(Strategy.model_fields)  # pydantic v2 fields, not class attrs
    keys = [k for k in param_grid if k in valid]
    if not keys or not all(isinstance(param_grid[k], (list, tuple)) for k in keys):
        return []
    combos = list(product(*(param_grid[k] for k in keys)))
    candidates: list[dict] = []
    for values in combos:
        if len(candidates) >= limit:
            break
        cfg = dict(base_config)
        cfg.update(dict(zip(keys, values)))
        try:
            Strategy.model_validate(cfg)      # enforces fast < slow and ranges
        except ValueError:
            continue
        candidates.append(cfg)
    return candidates


def rank_candidates(candidates: list[dict], metrics: dict) -> list[dict]:
    """Rank candidates by a composite score of their backtest metrics.

    Score = 0.30*win_rate + 0.30*profit_factor + 0.20*sharpe + 0.20*(1 - max_dd)
    Each metric is normalized by the best value across the pool, so the composite
    is a bounded 0..1 ranking, not an absolute figure.

    Candidates may already carry a ``'backtest'`` dict (metrics keyed by the
    candidate's stable ``_config_key`` is honored as a fallback). Candidates with
    no trades keep score 0.0 and sink to the bottom.
    """
    if not candidates:
        return []

    best_win = best_pf = best_sharpe = 0.0
    best_dd = 1.0
    for m in metrics.values():
        best_win = max(best_win, m.get('win_rate', 0))
        best_pf = max(best_pf, m.get('profit_factor', 0))
        best_sharpe = max(best_sharpe, m.get('sharpe', 0))
        best_dd = min(best_dd, m.get('max_drawdown', 0))

    ranked = []
    for cfg in candidates:
        m = cfg.get('backtest') or metrics.get(_config_key(cfg)) or {}
        if not m.get('trade_count'):
            ranked.append({**cfg, 'backtest': m, 'composite_score': 0.0})
            continue
        win, pf, sharpe, dd = (m.get('win_rate', 0), m.get('profit_factor', 0),
                               m.get('sharpe', 0), m.get('max_drawdown', 0))
        score = (0.30 * (win / best_win if best_win else 0)
                 + 0.30 * (pf / best_pf if best_pf else 0)
                 + 0.20 * (sharpe / best_sharpe if best_sharpe else 0)
                 + 0.20 * (1 - (dd / best_dd if best_dd else 0)))
        ranked.append({**cfg, 'backtest': m, 'composite_score': round(min(max(score, 0), 1), 4)})

    return sorted(ranked, key=lambda r: r['composite_score'], reverse=True)


def _config_key(cfg: dict) -> str:
    """Stable serialization for metrics lookup: sorted by key for reproducibility."""
    return str(sorted((str(k), str(v)) for k, v in cfg.items() if k != 'name'))