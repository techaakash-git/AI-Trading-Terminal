from __future__ import annotations
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from ..core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
logger = logging.getLogger(__name__)
database_available = False

class Base(DeclarativeBase):
    pass

async def init_db():
    global database_available
    from .models import CandleRecord
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        database_available = True
    except SQLAlchemyError:
        database_available = False
        logger.warning('Database unavailable; continuing without candle persistence', exc_info=True)
    return database_available
