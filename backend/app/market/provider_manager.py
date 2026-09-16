from __future__ import annotations
import logging
import time

from .exceptions import RateLimitExceeded
from .providers.base import MarketProvider
from .providers.demo import DemoMarketProvider
from .providers.free import FreeMarketProvider
from .providers.twelve_data import TwelveDataProvider
from ..core.config import settings

logger = logging.getLogger(__name__)

# Skip a rate-limited provider for this long before trying it again. Must be
# larger than the stream poll interval (60s) so a hit 429 has time to cool.
RATE_LIMIT_COOLDOWN_SECONDS = 300


class ProviderManager:
    """Rate-limit watcher over an ordered list of providers.

    Each provider is tried in priority order. When a provider raises
    :class:`RateLimitExceeded` (HTTP 429), the manager puts it on a cooldown
    timer and transparently switches to the next provider. The rate-limited
    provider is retried once the cooldown expires, so normal service resumes
    automatically when the limit clears. Non-rate-limit failures simply move to
    the next provider without a cooldown.
    """

    def __init__(self, providers: list[MarketProvider], cooldown: int = RATE_LIMIT_COOLDOWN_SECONDS):
        if not providers:
            raise ValueError('ProviderManager needs at least one provider')
        self.providers = providers
        self.cooldown = cooldown
        self._cooldown_until: dict[int, float] = {}
        self._active: int | None = None
        self._last_error: str | None = None
        self._label = [getattr(p, 'name', type(p).__name__) for p in providers]

    # -- internals ----------------------------------------------------------

    def _label_of(self, i: int) -> str:
        return self._label[i]

    def _available(self) -> list[int]:
        now = time.time()
        return [i for i in range(len(self.providers)) if self._cooldown_until.get(i, 0) <= now]

    def _put_on_cooldown(self, i: int):
        until = time.time() + self.cooldown
        self._cooldown_until[i] = until
        self._last_error = f'{self._label_of(i)} rate-limited until {int(until)}'
        logger.warning('Market provider %s is rate-limited; falling back to the next provider for %ss',
                       self._label_of(i), self.cooldown)

    def _mark_ok(self, i: int):
        self._cooldown_until.pop(i, None)
        self._active = i
        # Only a success from the configured primary provider (index 0) clears
        # last_error. A fallback success must keep the primary's failure visible
        # so status reports *why* the app is degraded.
        if i == 0:
            self._last_error = None

    def _record(self, i: int, exc: Exception):
        self._last_error = f'{self._label_of(i)}: {type(exc).__name__}'

    # -- public API ---------------------------------------------------------

    async def latest_tick(self, symbol: str):
        last_exc: Exception | None = None
        for i in self._available():
            try:
                tick = await self.providers[i].latest_tick(symbol)
                self._mark_ok(i)
                return tick
            except RateLimitExceeded as exc:
                self._put_on_cooldown(i)
                last_exc = exc
            except Exception as exc:
                self._record(i, exc)
                last_exc = exc
        if self._active is not None:
            # Every provider failed on this symbol; surface the last one but
            # keep serving from a previously-successful provider if possible.
            pass
        raise last_exc or RuntimeError('No market provider available')

    async def historical(self, symbol: str, timeframe: str, limit: int):
        last_exc: Exception | None = None
        for i in self._available():
            try:
                candles = await self.providers[i].historical(symbol, timeframe, limit)
                self._mark_ok(i)
                return candles
            except RateLimitExceeded as exc:
                self._put_on_cooldown(i)
                last_exc = exc
            except Exception as exc:
                self._record(i, exc)
                last_exc = exc
        raise last_exc or RuntimeError('No market provider available')

    def status(self) -> dict:
        now = time.time()

        def state(i: int) -> dict:
            expiry = self._cooldown_until.get(i, 0)
            return {
                'name': self._label_of(i),
                'active': self._active == i,
                'rate_limited': expiry > now,
                'rate_limited_until': int(expiry) if expiry > now else None,
            }

        active_label = self._label_of(self._active) if self._active is not None else None
        return {
            'configured_provider': settings.market_provider,
            'active_source': active_label,
            'degraded': active_label in ('free-public', 'development-demo'),
            'last_error': self._last_error,
            'providers': [state(i) for i in range(len(self.providers))],
        }


def build_manager() -> ProviderManager:
    """Assemble the provider chain from configuration.

    Priority: configured keyed provider (Twelve Data) -> keyless public sources
    (free-public: gold-api.com / Binance) -> deterministic development demo.
    """
    providers: list[MarketProvider] = []
    if settings.market_provider == 'twelvedata' and settings.market_api_key:
        providers.append(TwelveDataProvider(settings.market_api_key))
    providers.append(FreeMarketProvider())
    providers.append(DemoMarketProvider())
    return ProviderManager(providers)