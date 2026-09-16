from __future__ import annotations
from .provider_manager import build_manager

# The manager owns provider selection and failover. It starts from config and
# transparently switches providers when one is rate-limited (HTTP 429).
_manager = build_manager()


def provider_status() -> dict:
    """Current provider chain state: active source, degradation, and the
    rate-limit/cooldown status of every provider in the chain."""
    return _manager.status()


async def get_candles(symbol: str, timeframe: str, limit: int = 300):
    symbol = symbol.upper()
    limit = min(max(limit, 50), 5000)
    return await _manager.historical(symbol, timeframe, limit)


async def get_tick(symbol: str):
    symbol = symbol.upper()
    return await _manager.latest_tick(symbol)
