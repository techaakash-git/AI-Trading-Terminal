from __future__ import annotations
import asyncio
import logging
from collections.abc import AsyncGenerator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from ..core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
async_session_maker = SessionLocal  # alias used by realtime alert processor
logger = logging.getLogger(__name__)
database_available = False

class Base(DeclarativeBase):
    pass

async def init_db():
    global database_available
    from .models import CandleRecord  # noqa: F401 — ensures table is registered
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        database_available = True
    except (SQLAlchemyError, OSError, asyncio.TimeoutError):
        # Connection-level failures (ConnectionRefused, DNS, timeout) raise
        # OSError/TimeoutError, which SQLAlchemy does NOT wrap in SQLAlchemyError.
        # Treat any DB availability failure as fatal-to-persistence only, not to
        # the app — the whole point of graceful degradation here.
        database_available = False
        logger.warning('Database unavailable; continuing without candle persistence', exc_info=True)
    return database_available

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session per request."""
    async with SessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise
