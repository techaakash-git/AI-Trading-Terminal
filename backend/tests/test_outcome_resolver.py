"""Phase 15 — outcome evaluation tests.

These verify the no-lookahead walk-forward heart of the learning engine:
`evaluate_outcome` classifies a trade using only post-entry candles, never
future data.
"""
import asyncio

from app.learning.outcome_resolver import evaluate_outcome, OutcomeResolver, MAX_BARS
from app.market.models import Candle


def _candle_series(price, step=0.0, n=50):
    return [
        Candle(time=i, open=price + i * step, high=(price + i * step + 1),
               low=(price + i * step - 1), close=price + i * step, volume=1)
        for i in range(n)
    ]


def test_long_target_hit_is_win():
    # Entry 100, stop 98, target 106. Candle 3 high crosses 106 -> win.
    candles = [
        Candle(time=1, open=100, high=101, low=99, close=100, volume=1),
        Candle(time=2, open=100, high=102, low=99, close=101, volume=1),
        Candle(time=3, open=101, high=107, low=100, close=106, volume=1),
    ]
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['outcome'] == 'win'
    assert r['exit_price'] == 106.0
    assert r['bars_held'] == 3
    assert r['pnl_pct'] == round(6.0, 4)


def test_long_stop_hit_is_loss():
    candles = [
        Candle(time=1, open=100, high=101, low=97.5, close=98, volume=1),  # stop 98 hit
    ]
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['outcome'] == 'loss'
    assert r['exit_price'] == 98.0
    assert r['pnl_pct'] == round(-2.0, 4)


def test_long_stop_before_target_both_touched_same_bar():
    # Conservative tie-break: same-bar stop+target resolves as stop (loss).
    candles = [
        Candle(time=1, open=100, high=107, low=97.5, close=100, volume=1),
    ]
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['outcome'] == 'loss'
    assert r['exit_price'] == 98.0


def test_short_target_hit_is_win():
    candles = [
        Candle(time=1, open=100, high=100, low=95, close=96, volume=1),
    ]
    r = evaluate_outcome('short', 100.0, 103.0, 96.0, candles)
    assert r['outcome'] == 'win'
    assert r['exit_price'] == 96.0
    assert r['pnl_pct'] == round(4.0, 4)


def test_timeout_after_max_bars():
    # Flat, never hits stop/target -> breakeven (exit == entry).
    candles = _candle_series(100.0, step=0.0, n=MAX_BARS)
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['outcome'] == 'breakeven'
    assert r['bars_held'] == MAX_BARS
    assert r['pnl_pct'] == 0.0


def test_timeout_with_drift_is_timeout():
    # Slight drift without hitting barriers -> timeout.
    candles = _candle_series(100.0, step=0.01, n=MAX_BARS)
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['outcome'] == 'timeout'
    assert r['bars_held'] == MAX_BARS


def test_mfe_mae_tracked():
    candles = [
        Candle(time=1, open=100, high=102, low=99, close=101, volume=1),
        Candle(time=2, open=101, high=103, low=98.5, close=99, volume=1),
    ]
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['max_favorable'] == round(3.0, 4)   # high 103
    assert r['max_adverse'] == round(1.5, 4)     # low 98.5
    assert r['outcome'] == 'timeout'             # neither barrier yet


def test_breakeven_when_exit_equals_entry():
    candles = [Candle(time=1, open=100, high=101, low=99, close=100, volume=1)]
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, candles)
    assert r['outcome'] == 'breakeven'
    assert r['pnl_pct'] == 0.0


def test_no_candles_timeout():
    r = evaluate_outcome('long', 100.0, 98.0, 106.0, [])
    assert r['outcome'] == 'timeout'


def test_short_favorable_adverse_directional():
    candles = [
        Candle(time=1, open=100, high=101, low=97, close=98, volume=1),
    ]
    r = evaluate_outcome('short', 100.0, 104.0, 95.0, candles)
    assert r['max_favorable'] == round(3.0, 4)   # entry 100 -> low 97
    assert r['max_adverse'] == round(1.0, 4)     # entry 100 -> high 101


def test_resolver_resolves_a_signal_end_to_end():
    """Feed the resolver a fake session + feed; one unresolved signal gets an
    outcome row and is flagged resolved."""
    from datetime import datetime
    created_at = datetime(2026, 1, 1)
    entry_ts = int(created_at.timestamp())  # candles must be epoch-later than entry

    class FakeFeed:
        def __init__(self):
            self.candles = [
                Candle(time=entry_ts + 1, open=100, high=101, low=99, close=100, volume=1),
                Candle(time=entry_ts + 2, open=100, high=107, low=100, close=106, volume=1),  # target 106
            ]
        async def __call__(self, symbol, tf, limit):
            return self.candles

    class Signal:
        id, resolved = 1, False
        symbol, timeframe = 'XAUUSD', '1h'
        direction, entry_price = 'long', 100.0
        stop_loss, target = 98.0, 106.0
        created_at = datetime(2026, 1, 1)

    class FakeResult:
        def __init__(self, signals): self.signals = signals
        def scalars(self): return self
        def all(self): return self.signals

    class FakeSession:
        def __init__(self, signals):
            self.signals = signals
            self.captured = {}
        async def execute(self, q):
            return FakeResult(self.signals)
        async def commit(self):
            self.captured['committed'] = True
        async def close(self): pass
        def add(self, obj):
            self.captured['outcome'] = obj

    async def _drive():
        resolver = OutcomeResolver()
        session = FakeSession([Signal()])
        resolver._get_session = lambda: session
        resolver._get_candles = FakeFeed()
        await resolver._resolve_once()
        return session.captured

    captured = asyncio.run(_drive())
    assert captured['committed'] is True
    assert captured['outcome'].signal_id == 1
    assert captured['outcome'].outcome == 'win'
    assert captured['outcome'].exit_price == 106.0