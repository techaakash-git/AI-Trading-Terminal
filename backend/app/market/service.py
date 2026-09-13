from .providers.demo import DemoMarketProvider
from .providers.twelve_data import TwelveDataProvider
from ..core.config import settings

_demo = DemoMarketProvider()
_real = TwelveDataProvider(settings.market_api_key) if settings.market_api_key else None
_last_source = 'development-demo'
_last_error: str | None = None

def provider_status():
    return {
        'configured_provider': settings.market_provider,
        'active_source': _last_source,
        'degraded': _last_source == 'development-demo' and settings.market_provider != 'demo',
        'last_error': _last_error,
    }

async def get_candles(symbol: str, timeframe: str, limit: int = 300):
    global _last_source, _last_error
    symbol=symbol.upper(); limit=min(max(limit,50),5000)
    if settings.market_provider == 'twelvedata' and _real:
        try:
            result = await _real.historical(symbol,timeframe,limit)
            _last_source, _last_error = 'twelve-data', None
            return result
        except Exception as exc:
            _last_error = type(exc).__name__
    _last_source = 'development-demo'
    return await _demo.historical(symbol,timeframe,limit)

async def get_tick(symbol: str):
    global _last_source, _last_error
    symbol=symbol.upper()
    if settings.market_provider == 'twelvedata' and _real:
        try:
            result = await _real.latest_tick(symbol)
            _last_source, _last_error = 'twelve-data', None
            return result
        except Exception as exc:
            _last_error = type(exc).__name__
    _last_source = 'development-demo'
    return await _demo.latest_tick(symbol)
