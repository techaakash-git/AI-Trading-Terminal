import asyncio
import json

from app.market.models import Candle
from app.market.realtime import RealtimeHub


class OfflineRedis:
    def pubsub(self):
        raise OSError('Redis unavailable')

    async def publish(self, *_args):
        raise OSError('Redis unavailable')


def test_local_fallback_delivers_candle_when_redis_is_offline():
    async def exercise():
        hub = RealtimeHub()
        hub.redis = OfflineRedis()
        subscription = await hub.subscribe('BTCUSDT', '1m')
        await hub.publish_candle('BTCUSDT', '1m', Candle(time=60, open=100, high=101, low=99, close=100.5, volume=2))
        event = await subscription.get_message(timeout=0.1)
        await subscription.close()
        return event

    event = asyncio.run(exercise())
    payload = json.loads(event['data'])
    assert payload['type'] == 'candle'
    assert payload['data']['close'] == 100.5
