from __future__ import annotations
import time
from .provider_manager import build_manager

# The manager owns provider selection and failover. It starts from config and
# transparently switches providers when one is rate-limited (HTTP 429).
_manager = build_manager()

# Historical candle cache: a 300-point chart costs ~300 Twelve Data credits,
# so repeated page loads/refreshes must reuse the last fetch instead of
# burning the daily budget. Only results served by the primary provider are
# cached; degraded/free fallback data is never frozen in the cache.
_CANDLE_CACHE_TTL_S = 100
_candle_cache: dict[tuple, tuple[float, list]] = {}


def provider_status() -> dict:
    """Current provider chain state: active source, degradation, and the
    rate-limit/cooldown status of every provider in the chain."""
    return _manager.status()


async def get_candles(symbol: str, timeframe: str, limit: int = 300, refresh: bool = False):
    symbol = symbol.upper()
    limit = min(max(limit, 50), 5000)
    cache_key = (symbol, timeframe, limit)

    if refresh:
        _candle_cache.pop(cache_key, None)

    cached = _candle_cache.get(cache_key)
    if cached is not None and not refresh:
        cached_at, candles = cached
        if time.time() - cached_at <= _CANDLE_CACHE_TTL_S:
            return candles
        _candle_cache.pop(cache_key, None)

    candles = await _manager.historical(symbol, timeframe, limit)

    # Cache only when the configured primary provider actually served (first in
    # the chain). While degraded onto a fallback, next request retries the
    # primary promptly instead of serving frozen fallback data.
    providers = _manager.status().get('providers', [])
    primary = providers[0]['name'] if providers else None
    if primary and _manager.status().get('active_source') == primary:
        _candle_cache[cache_key] = (time.time(), candles)
    return candles


async def get_tick(symbol: str):
    symbol = symbol.upper()
    return await _manager.latest_tick(symbol)