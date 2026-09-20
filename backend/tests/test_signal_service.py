"""Phase 15 — signal service tests (record / query / outcome pairing).

Uses an in-memory async SQLite engine, matching the hermetic pattern from
test_learning_models.py. No Postgres needed.
"""
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.database import Base
from app.db import models as m
from app.schemas.learning import SignalCreate
from app.learning.signal_service import (
    record_signal,
    get_signals,
    get_signals_count,
    get_signal,
    get_outcomes,
    get_signal_with_outcome,
)


def _factory():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_init())

    async def _dispose():
        await engine.dispose()
    factory.close_extra = _dispose  # type: ignore[attr-defined]
    return factory


def _payload(**over):
    base = dict(
        symbol='XAUUSD', timeframe='1h',
        strategy_config={'fast': 20, 'slow': 50, 'risk_pct': 1.0},
        indicators_snapshot={'trend': 'bullish', 'rsi14': 42.0},
        direction='long', entry_price=2400.0,
        stop_loss=2380.0, target=2440.0, data_quality='live',
    )
    base.update(over)
    return SignalCreate(**base)


def test_record_signal_persists_and_uppercases_symbol():
    async def _run(factory):
        session = factory()
        try:
            sig = await record_signal(session, _payload(symbol='xauusd'))
            assert sig.id is not None
            assert sig.symbol == 'XAUUSD'       # normalized uppercase
            assert sig.direction == 'long'
            assert sig.resolved is False
            assert sig.entry_price == 2400.0
        finally:
            await session.close()
    asyncio.run(_run(_factory()))


def test_get_signals_filters_by_symbol_and_resolved():
    async def _run(factory):
        session = factory()
        try:
            await record_signal(session, _payload(symbol='AAPL', direction='long'))
            await record_signal(session, _payload(symbol='AAPL', direction='short'))
            await record_signal(session, _payload(symbol='MSFT', direction='long'))

            aapl = await get_signals(session, symbol='aapl')      # case-insensitive filter
            assert len(aapl) == 2
            assert all(s.symbol == 'AAPL' for s in aapl)

            # Mark the MSFT long resolved; resolved filter must partition them.
            msft = await get_signals(session, symbol='MSFT')
            msft[0].resolved = True
            await session.commit()

            pending = await get_signals(session, resolved=False)
            assert len(pending) == 2                      # the two AAPL signals
            assert all(not s.resolved for s in pending)

            done = await get_signals(session, resolved=True)
            assert len(done) == 1 and done[0].symbol == 'MSFT'

            assert await get_signals_count(session, resolved=False) == 2
            assert await get_signals_count(session, resolved=True) == 1
        finally:
            await session.close()
    asyncio.run(_run(_factory()))


def test_get_signals_limit_and_newest_first():
    async def _run(factory):
        session = factory()
        try:
            for i in range(5):
                await record_signal(session, _payload(entry_price=2400.0 + i))
            all_sigs = await get_signals(session, limit=3)
            assert len(all_sigs) == 3
            prices = [s.entry_price for s in all_sigs]
            assert prices == sorted(prices, reverse=True)  # newest (highest price) first
        finally:
            await session.close()
    asyncio.run(_run(_factory()))


def test_get_signal_returns_none_for_missing():
    async def _run(factory):
        session = factory()
        try:
            assert await get_signal(session, 999) is None
        finally:
            await session.close()
    asyncio.run(_run(_factory()))


def test_get_outcomes_scoped_to_signal():
    async def _run(factory):
        session = factory()
        try:
            sig = await record_signal(session, _payload())

            rows = [m.SignalOutcome(signal_id=sig.id, outcome=o, pnl_pct=p,
                                    max_favorable=1.0, max_adverse=0.5,
                                    bars_held=5, exit_price=2420.0)
                    for o, p in [('win', 2.0), ('loss', -1.0)]]
            session.add_all(rows)
            await session.commit()

            outcomes = await get_outcomes(session, signal_id=sig.id)
            assert len(outcomes) == 2
            assert all(o.signal_id == sig.id for o in outcomes)
        finally:
            await session.close()
    asyncio.run(_run(_factory()))


def test_get_signal_with_outcome_pairs():
    async def _run(factory):
        session = factory()
        try:
            sig = await record_signal(session, _payload())
            session.add(m.SignalOutcome(signal_id=sig.id, outcome='win', pnl_pct=3.0,
                                        max_favorable=4.0, max_adverse=0.0,
                                        bars_held=8, exit_price=2472.0))
            await session.commit()

            pair = await get_signal_with_outcome(session, sig.id)
            assert pair['signal'].id == sig.id
            assert pair['outcome'].outcome == 'win'
            # Unresolved signal has no outcome yet.
            fresh = await record_signal(session, _payload(direction='short'))
            pair2 = await get_signal_with_outcome(session, fresh.id)
            assert pair2['outcome'] is None
        finally:
            await session.close()
    asyncio.run(_run(_factory()))