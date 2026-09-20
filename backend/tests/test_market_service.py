import asyncio
from datetime import datetime, timezone

from app.core.config import settings
from app.market import service, stream
from app.market.models import Tick
from app.market.providers.demo import DemoMarketProvider
from app.market.provider_manager import ProviderManager


def test_service_wires_through_manager_and_degrades_to_demo(monkeypatch):
    # The manager is built from config at import time. Swap in a fixed chain
    # (demo only) so the test is deterministic and never touches the network.
    service._manager = ProviderManager([DemoMarketProvider()])

    candles = asyncio.run(service.get_candles('BTCUSDT', '1h', 50))
    assert len(candles) == 50

    status = service.provider_status()
    assert status['active_source'] == 'development-demo'
    assert status['degraded'] is True
    assert any(p['name'] == 'development-demo' for p in status['providers'])


def test_demo_chain_reports_no_rate_limit(monkeypatch):
    service._manager = ProviderManager([DemoMarketProvider()])

    asyncio.run(service.get_tick('XAUUSD'))
    status = service.provider_status()
    assert status['last_error'] is None
    assert all(p['rate_limited'] is False for p in status['providers'])


def test_stream_prefers_configured_provider_over_free_public_fallback(monkeypatch):
    async def fake_get_tick(symbol):
        return Tick(symbol=symbol, price=1234.56, timestamp=datetime.now(timezone.utc), volume=42.0)

    async def fake_free_tick(symbol):
        raise AssertionError('free public fallback should not be used while configured provider is available')

    monkeypatch.setattr(stream, 'get_tick', fake_get_tick)
    monkeypatch.setattr(stream._free_provider, 'latest_tick', fake_free_tick)

    tick = asyncio.run(stream._stream_tick('XAUUSD'))
    assert tick.price == 1234.56
    assert tick.symbol == 'XAUUSD'