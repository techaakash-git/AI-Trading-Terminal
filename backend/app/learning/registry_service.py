"""Phase 15 — strategy candidate discovery, validation, promotion & registry.

The hard math (grid backtests, walk-forward splits) stays in app/engine and
app/strategies; this module is the thin persistence layer around it. Promotion
from candidate -> registry is a *human* decision: an endpoint calls it, no code
ever auto-deploys a strategy.
"""
from __future__ import annotations

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import StrategyCandidate, StrategyRegistry, TrainingRun


# ---------------------------------------------------------------- candidates
async def list_candidates(db: AsyncSession, status: str | None = None,
                          limit: int = 100, offset: int = 0) -> list[StrategyCandidate]:
    q = select(StrategyCandidate).order_by(desc(StrategyCandidate.created_at))
    if status:
        q = q.where(StrategyCandidate.status == status)
    q = q.limit(min(max(limit, 1), 500)).offset(max(offset, 0))
    return list((await db.execute(q)).scalars().all())


async def create_candidates(db: AsyncSession, configs: list[dict],
                            backtest_metrics: dict | None = None) -> list[StrategyCandidate]:
    """Persist grid-search results. Each candidate gets its own backtest metrics."""
    rows = []
    for cfg in configs:
        keyed = backtest_metrics or {}
        m = keyed.get(_config_key(cfg), keyed.get(str(cfg), {})) or {}
        rows.append(StrategyCandidate(config=cfg, backtest_metrics=m))
    db.add_all(rows)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows


async def get_candidate(db: AsyncSession, candidate_id: int) -> StrategyCandidate | None:
    return await db.get(StrategyCandidate, candidate_id)


async def set_candidate_validated(db: AsyncSession, candidate: StrategyCandidate,
                                  walk_forward: dict, oos: dict, status: str = 'validated') -> StrategyCandidate:
    """Attach walk-forward + out-of-sample results to a discovered candidate."""
    candidate.walk_forward_metrics = walk_forward
    candidate.oos_metrics = oos
    candidate.status = status
    await db.commit()
    await db.refresh(candidate)
    return candidate


# ---------------------------------------------------------------- registry
async def list_registry(db: AsyncSession, status: str | None = None,
                        limit: int = 100) -> list[StrategyRegistry]:
    q = select(StrategyRegistry).order_by(desc(StrategyRegistry.created_at))
    if status:
        q = q.where(StrategyRegistry.status == status)
    q = q.limit(min(max(limit, 1), 500))
    return list((await db.execute(q)).scalars().all())


async def promote_candidate(db: AsyncSession, candidate: StrategyCandidate, name: str) -> StrategyRegistry:
    """Human-approved promotion. Copies the validated config + OOS metrics into
    the registry. Candidate status becomes 'promoted'."""
    existing = (await db.execute(
        select(StrategyRegistry).where(StrategyRegistry.name == name))).scalars().first()
    if existing:
        raise ValueError('a strategy with that name already exists')
    oos = dict(candidate.oos_metrics)
    entry = StrategyRegistry(
        name=name, version=1, config=dict(candidate.config), status='active',
        win_rate=oos.get('win_rate'), profit_factor=oos.get('profit_factor'),
        sharpe=oos.get('sharpe'), max_drawdown=oos.get('max_drawdown'),
        trade_count=int(oos.get('trade_count', 0)),
    )
    db.add(entry)
    candidate.status = 'promoted'
    await db.commit()
    await db.refresh(entry)
    await db.refresh(candidate)
    return entry


async def update_strategy_status(db: AsyncSession, strategy: StrategyRegistry,
                                 status: str) -> StrategyRegistry:
    strategy.status = status
    await db.commit()
    await db.refresh(strategy)
    return strategy


async def get_registry_strategy(db: AsyncSession, strategy_id: int) -> StrategyRegistry | None:
    return await db.get(StrategyRegistry, strategy_id)


# ---------------------------------------------------------------- training runs
async def list_training_runs(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[TrainingRun]:
    q = (select(TrainingRun).order_by(desc(TrainingRun.created_at))
         .limit(min(max(limit, 1), 200)).offset(max(offset, 0)))
    return list((await db.execute(q)).scalars().all())


async def record_training_run(db: AsyncSession, model_type: str, metrics: dict,
                              sample_count: int, symbol: str | None = None,
                              feature_importance: dict | None = None) -> TrainingRun:
    row = TrainingRun(model_type=model_type, symbol=symbol, metrics=metrics,
                      sample_count=sample_count, feature_importance=feature_importance)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


def _config_key(cfg: dict) -> str:
    """Same stable serialization as candidate_service so metrics line up."""
    return str(sorted((str(k), str(v)) for k, v in cfg.items() if k != 'name'))