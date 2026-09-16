import asyncio
from datetime import datetime, timezone

from app.market.exceptions import RateLimitExceeded
from app.market.models import Candle, Tick
from app.market.providers.base import MarketProvider
from app.market.provider_manager import ProviderManager


class BoomProvider(MarketProvider):
    """Always raises RateLimitExceeded (simulated HTTP 429)."""
    name = 'boom'

    async def latest_tick(self, symbol):
        raise RateLimitExceeded('429 simulated')

    async def historical(self, symbol, timeframe, limit):
        raise RateLimitExceeded('429 simulated')


class FailNTimesProvider(MarketProvider):
    """Rate-limits the first N calls, then succeeds."""
    name = 'flaky'

    def __init__(self, fail_times: int):
        self.fail_times = fail_times

    async def latest_tick(self, symbol):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RateLimitExceeded('429 simulated')
        return Tick(symbol='XAUUSD', price=100.0, timestamp=datetime.now(timezone.utc), volume=1.0)

    async def historical(self, symbol, timeframe, limit):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RateLimitExceeded('429 simulated')
        return [Candle(time=1, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)]


class ErrorProvider(MarketProvider):
    """Fails with a generic, non-rate-limit error."""
    name = 'error'

    async def latest_tick(self, symbol):
        raise ConnectionError('down')

    async def historical(self, symbol, timeframe, limit):
        raise ConnectionError('down')


class GoodProvider(MarketProvider):
    name = 'good'

    async def latest_tick(self, symbol):
        return Tick(symbol='XAUUSD', price=2000.0, timestamp=datetime.now(timezone.utc), volume=2.0)

    async def historical(self, symbol, timeframe, limit):
        return [Candle(time=2, open=2.0, high=2.0, low=2.0, close=2.0, volume=2.0)]


def test_switches_to_fallback_and_marks_primary_rate_limited():
    pm = ProviderManager([BoomProvider(), GoodProvider()], cooldown=300)
    tick = asyncio.run(pm.latest_tick('XAUUSD'))
    assert tick.price == 2000.0  # served by the fallback, not the rate-limited primary

    s = pm.status()
    assert s['active_source'] == 'good'
    assert s['providers'][0]['rate_limited'] is True
    assert s['providers'][0]['rate_limited_until'] is not None
    assert s['providers'][0]['rate_limited_until'] > s['providers'][1]['rate_limited_until'] if s['providers'][1]['rate_limited_until'] else True
    assert s['providers'][1]['rate_limited'] is False


def test_generic_error_does_not_set_rate_limit_flag():
    pm = ProviderManager([ErrorProvider(), GoodProvider()], cooldown=300)
    tick = asyncio.run(pm.latest_tick('XAUUSD'))
    assert tick.price == 2000.0
    s = pm.status()
    assert s['providers'][0]['rate_limited'] is False  # ConnectionError != 429
    assert s['last_error'] is not None


def test_retries_rate_limited_provider_after_cooldown_expires():
    # cooldown=0 => the watcher retries the primary on the very next call.
    pm = ProviderManager([FailNTimesProvider(fail_times=1), GoodProvider()], cooldown=0)
    tick1 = asyncio.run(pm.latest_tick('XAUUSD'))
    assert tick1.price == 2000.0  # primary 429'd -> fallback served
    tick2 = asyncio.run(pm.latest_tick('XAUUSD'))
    assert tick2.price == 100.0  # primary recovered -> served again
    s = pm.status()
    assert s['active_source'] == 'flaky'
    assert s['providers'][0]['rate_limited'] is False


def test_continuous_failover_while_primary_keeps_rate_limiting():
    pm = ProviderManager([FailNTimesProvider(fail_times=3), GoodProvider()], cooldown=0)
    prices = [asyncio.run(pm.latest_tick('XAUUSD')).price for _ in range(4)]
    assert prices == [2000.0, 2000.0, 2000.0, 100.0]  # 3 fails, then primary recovers


def test_long_cooldown_skips_rate_limited_provider_entirely():
    pm = ProviderManager([FailNTimesProvider(fail_times=3), GoodProvider()], cooldown=300)
    prices = [asyncio.run(pm.latest_tick('XAUUSD')).price for _ in range(3)]
    assert prices == [2000.0, 2000.0, 2000.0]  # primary on cooldown the whole time


def test_historical_falls_back_on_rate_limit():
    pm = ProviderManager([BoomProvider(), GoodProvider()], cooldown=300)
    candles = asyncio.run(pm.historical('XAUUSD', '1h', 50))
    assert candles[0].close == 2.0