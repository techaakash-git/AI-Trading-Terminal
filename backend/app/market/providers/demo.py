import math
import random
from datetime import datetime, timezone
from .base import MarketProvider
from ..models import Candle, Tick

class DemoMarketProvider(MarketProvider):
    # Development-only deterministic market simulator.
    def _base(self, symbol: str) -> float:
        return 65000.0 if symbol.upper() == "BTCUSDT" else 2350.0

    async def historical(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        base = self._base(symbol)
        step = {"1m":60, "5m":300, "15m":900, "1h":3600, "4h":14400, "1d":86400}.get(timeframe, 3600)
        now = int(datetime.now(timezone.utc).timestamp())
        data, price = [], base
        for i in range(limit):
            drift = math.sin(i / 14) * base * 0.002
            noise = math.sin(i * 2.13) * base * 0.0007
            close = max(0.01, price + drift + noise)
            high = max(price, close) + abs(math.sin(i * 0.71)) * base * 0.001
            low = min(price, close) - abs(math.cos(i * 0.47)) * base * 0.001
            data.append(Candle(time=now-(limit-i)*step, open=price, high=high, low=low, close=close, volume=100+i))
            price = close
        return data

    async def latest_tick(self, symbol: str) -> Tick:
        candles = await self.historical(symbol, "1m", 2)
        last = candles[-1].close
        return Tick(
            symbol=symbol.upper(),
            price=max(0.01, last + (random.random()-0.5) * last * 0.00015),
            timestamp=datetime.now(timezone.utc),
            volume=random.uniform(1, 10),
        )
