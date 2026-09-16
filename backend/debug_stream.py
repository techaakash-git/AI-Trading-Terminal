import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

from app.market.stream import MarketStream
from app.market.service import get_tick
from app.market.aggregator import CandleAggregator, TIMEFRAME_SECONDS
from app.market.realtime import hub

async def test():
    print('Starting stream manually...')
    s = MarketStream()
    await s.start()
    print('Stream tasks:', list(s.tasks.keys()))

    # Wait a bit for data to flow
    await asyncio.sleep(8)

    # Check aggregators
    for key, agg in s.aggs.items():
        print(f'Aggregator {key}: current={agg.current}, last_closed={agg.last_closed}')

    # Check if hub has subscribers
    print('Hub local_subscribers:', dict(hub._local_subscribers))

    await s.stop()
    print('Stream stopped')

asyncio.run(test())