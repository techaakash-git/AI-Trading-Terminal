import asyncio

from app.core.config import settings
from app.market import service


def test_missing_provider_key_uses_explicit_demo_source(monkeypatch):
    monkeypatch.setattr(settings, 'market_provider', 'twelvedata')
    monkeypatch.setattr(service, '_real', None)
    candles = asyncio.run(service.get_candles('BTCUSDT', '1h', 50))
    assert len(candles) == 50
    assert service.provider_status()['active_source'] == 'development-demo'
    assert service.provider_status()['degraded'] is True
