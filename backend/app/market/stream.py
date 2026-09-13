from __future__ import annotations
import asyncio
from datetime import datetime
from .service import get_tick
from .aggregator import CandleAggregator, TIMEFRAME_SECONDS
from .realtime import hub
from ..db.database import SessionLocal
from ..db.models import CandleRecord
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from ..core.config import settings

SYMBOLS = ('BTCUSDT','XAUUSD')
TIMEFRAMES = tuple(TIMEFRAME_SECONDS)

class MarketStream:
    def __init__(self):
        self.tasks: dict[str, asyncio.Task] = {}
        self.aggs = {(s,tf): CandleAggregator(tf) for s in SYMBOLS for tf in TIMEFRAMES}

    async def start(self):
        for symbol in SYMBOLS:
            self.tasks[symbol] = asyncio.create_task(self._run(symbol), name=f'market-{symbol}')

    async def stop(self):
        for task in self.tasks.values(): task.cancel()
        if self.tasks: await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()

    async def _persist(self, symbol, timeframe, candle):
        try:
            async with SessionLocal() as session:
                stmt = insert(CandleRecord).values(symbol=symbol,timeframe=timeframe,time=candle.time,open=candle.open,high=candle.high,low=candle.low,close=candle.close,volume=candle.volume)
                stmt = stmt.on_conflict_do_update(index_elements=['symbol','timeframe','time'], set_={'high':candle.high,'low':candle.low,'close':candle.close,'volume':candle.volume})
                await session.execute(stmt); await session.commit()
        except SQLAlchemyError:
            return

    async def _run(self, symbol):
        while True:
            tick = await get_tick(symbol)
            await hub.publish_tick(tick)
            for tf in TIMEFRAMES:
                candle, opened = self.aggs[(symbol,tf)].update(tick)
                await hub.publish_candle(symbol,tf,candle)
                closed = self.aggs[(symbol,tf)].last_closed
                if closed is not None:
                    await self._persist(symbol,tf,closed)
                    self.aggs[(symbol,tf)].last_closed = None
                await self._persist(symbol,tf,candle)
            await asyncio.sleep(1)

stream = MarketStream()
