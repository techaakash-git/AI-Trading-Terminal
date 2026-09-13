from __future__ import annotations
import asyncio, json, logging
from collections import defaultdict
try:
    import redis.asyncio as redis
except ImportError:  # Optional in local deterministic-development mode.
    redis = None
from .models import Tick, Candle
from .aggregator import CandleAggregator
from ..core.config import settings

class RealtimeHub:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True) if redis else None
        self._tasks = {}
        self._aggregators = {}
        self._local_subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self.redis_available = False

    def channel(self, symbol: str, timeframe: str) -> str:
        return f'market:{symbol.upper()}:{timeframe}'

    async def publish_tick(self, tick: Tick):
        payload = json.dumps({'type':'tick','data':tick.model_dump(mode='json')})
        await self._publish(f'tick:{tick.symbol.upper()}', payload)

    async def publish_candle(self, symbol: str, timeframe: str, candle: Candle):
        payload = json.dumps({'type':'candle','symbol':symbol.upper(),'timeframe':timeframe,'data':candle.model_dump()})
        await self._publish(self.channel(symbol,timeframe), payload)

    async def _publish(self, channel: str, payload: str):
        for queue in tuple(self._local_subscribers[channel]):
            if queue.full():
                _ = queue.get_nowait()
            queue.put_nowait(payload)
        try:
            if self.redis is None:
                raise OSError('Redis client is not installed')
            await self.redis.publish(channel, payload)
            self.redis_available = True
        except Exception:
            self.redis_available = False

    async def subscribe(self, symbol: str, timeframe: str):
        channel = self.channel(symbol, timeframe)
        try:
            if self.redis is None:
                raise OSError('Redis client is not installed')
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            self.redis_available = True
            return RedisSubscription(pubsub)
        except Exception:
            self.redis_available = False
            queue: asyncio.Queue[str] = asyncio.Queue(maxsize=32)
            self._local_subscribers[channel].add(queue)
            return LocalSubscription(queue, self._local_subscribers[channel])

class RedisSubscription:
    def __init__(self, pubsub): self.pubsub = pubsub
    async def get_message(self, timeout: float):
        return await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
    async def close(self):
        await self.pubsub.unsubscribe()
        await self.pubsub.close()

class LocalSubscription:
    def __init__(self, queue: asyncio.Queue[str], subscribers: set[asyncio.Queue[str]]):
        self.queue, self.subscribers = queue, subscribers
    async def get_message(self, timeout: float):
        try:
            return {'data': await asyncio.wait_for(self.queue.get(), timeout)}
        except asyncio.TimeoutError:
            return None
    async def close(self): self.subscribers.discard(self.queue)

hub = RealtimeHub()
