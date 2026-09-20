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

    # Retry mechanism to handle database startup race condition
    max_retries = 10
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            database_available = True
            logger.info("Database initialized successfully.")
            return True
        except (SQLAlchemyError, OSError, asyncio.TimeoutError):
            database_available = False
            if attempt < max_retries - 1:
                logger.warning(f'Database unavailable (attempt {attempt + 1}/{max_retries}); retrying in {retry_delay}s...')
                await asyncio.sleep(retry_delay)
            else:
                logger.error('Database unavailable after %d attempts; continuing without candle persistence', max_retries)
                return False

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session per request."""
    async with SessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise
