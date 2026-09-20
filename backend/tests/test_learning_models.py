"""Phase 15 — verify learning DB models register and tables build cleanly.

Uses an in-memory async SQLite engine so the test is hermetic (no Postgres
needed). The production URL is asyncpg/Postgres; the models use the portable
JSON type so both backends accept them.
"""
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

from app.db.database import Base
from app.db import models as m


def _engine():
    return create_async_engine('sqlite+aiosqlite:///:memory:')


def test_all_learning_tables_created():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        assert True
        await engine.dispose()
    asyncio.run(_run())


def test_trading_signals_columns():
    cols = {c.name for c in m.TradingSignal.__table__.columns}
    assert {'id', 'symbol', 'timeframe', 'strategy_config', 'indicators_snapshot',
            'direction', 'entry_price', 'stop_loss', 'target', 'data_quality',
            'resolved', 'created_at'} <= cols


def test_signal_outcome_has_foreign_key():
    assert 'signal_id' in {c.name for c in m.SignalOutcome.__table__.columns}
    # FK target resolves to trading_signals.id
    fk = list(m.SignalOutcome.__table__.foreign_keys)[0]
    assert fk.column.table.name == 'trading_signals'


def test_strategy_registry_unique_name():
    from sqlalchemy import UniqueConstraint
    uq = [c for c in m.StrategyRegistry.__table__.constraints if isinstance(c, UniqueConstraint)]
    assert uq and any('name' in [col.name for col in c.columns] for c in uq)


def test_regime_indexes():
    idx = [i.name for i in m.MarketRegime.__table__.indexes]
    assert 'ix_regime_symbol_tf' in idx


def test_learning_rows_persist_and_query():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            signal = m.TradingSignal(
                symbol='BTCUSDT', timeframe='1h',
                strategy_config={'fast': 20, 'slow': 50},
                indicators_snapshot={'trend': 'bullish'},
                direction='long', entry_price=60000.0,
                stop_loss=59000.0, target=62000.0, data_quality='degraded',
            )
            session.add(signal)
            await session.commit()
            await session.refresh(signal)

            outcome = m.SignalOutcome(
                signal_id=signal.id, outcome='win', pnl_pct=3.4,
                max_favorable=5.0, max_adverse=1.0, bars_held=12, exit_price=62000.0,
            )
            session.add(outcome)
            session.add(m.MarketRegime(
                symbol='BTCUSDT', timeframe='1h', trend='bullish',
                volatility='high', regime_label='bullish_trending_high_vol',
                indicators={'atr_pct': 1.2},
            ))
            await session.commit()

            result = await session.execute(select(m.TradingSignal))
            assert len(result.scalars().all()) == 1
            result = await session.execute(select(m.SignalOutcome))
            assert result.scalars().all()[0].outcome == 'win'
            result = await session.execute(select(func.count()).select_from(m.MarketRegime))
            assert result.scalar() == 1
        await engine.dispose()
    asyncio.run(_run())


def test_candidate_and_training_run_defaults():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            cand = m.StrategyCandidate(config={'fast': 10, 'slow': 40})
            run = m.TrainingRun(model_type='classifier', metrics={'accuracy': 0.55}, sample_count=100)
            session.add_all([cand, run])
            await session.commit()
            await session.refresh(cand)
            await session.refresh(run)
            # DB defaults applied for omitted columns
            assert cand.status == 'discovered'
            assert cand.backtest_metrics == {}
            assert run.sample_count == 100
        await engine.dispose()
    asyncio.run(_run())