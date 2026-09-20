"""Phase 15 — strategy candidate discovery & ranking tests."""
from app.strategies.candidate_service import generate_candidates, rank_candidates


def test_generate_candidates_respects_fast_lt_slow():
    grid = {'fast': [5, 40], 'slow': [20, 50]}   # 40/20 is invalid (fast >= slow)
    cands = generate_candidates({'risk_pct': 1.0}, grid)
    assert len(cands) == 3        # (5,20), (5,50), (40,50) — (40,20) skipped
    for c in cands:
        assert c['fast'] < c['slow']


def test_generate_candidates_honors_limit():
    grid = {'fast': [5, 10, 15], 'slow': [20, 30, 40]}
    cands = generate_candidates({}, grid, limit=4)
    assert len(cands) <= 4


def test_generate_candidates_ignores_unknown_params():
    grid = {'fast': [10], 'slow': [40], 'stop_atr_multiple': [1.5], 'nonsense': [1]}
    cands = generate_candidates({}, grid)
    assert len(cands) == 1
    assert 'nonsense' not in cands[0]


def test_generate_candidates_empty_grid():
    assert generate_candidates({}, {}) == []
    assert generate_candidates({}, {'fast': 10}) == []   # value, not list


def _bt(win_rate, pf, sharpe, dd, trades=10):
    return {'win_rate': win_rate, 'profit_factor': pf, 'sharpe': sharpe,
            'max_drawdown': dd, 'trade_count': trades}


def test_rank_candidates_best_first():
    from app.strategies.candidate_service import _config_key
    c1 = {'name': 'a', 'fast': 10, 'slow': 30}
    c2 = {'name': 'b', 'fast': 15, 'slow': 40}
    c3 = {'name': 'c', 'fast': 20, 'slow': 50}
    metrics = {
        _config_key(c1): _bt(0.60, 2.5, 1.2, 0.05),
        _config_key(c2): _bt(0.42, 1.1, 0.4, 0.20),
        _config_key(c3): _bt(0.45, 1.4, 0.8, 0.10),
    }
    ranked = rank_candidates([c1, c2, c3], metrics)
    assert ranked[0]['name'] == 'a'                     # highest win/pf/sharpe
    assert ranked[-1]['name'] == 'b'
    scores = [r['composite_score'] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_candidates_trade_count_gate():
    c = {'name': 'x', 'fast': 10, 'slow': 30}
    from app.strategies.candidate_service import _config_key
    metrics = {_config_key(c): _bt(0.9, 9.0, 3.0, 0.01, trades=0)}
    ranked = rank_candidates([c], metrics)
    assert ranked[0]['composite_score'] == 0.0          # zero trades => 0 score