from abc import ABC, abstractmethod
from ..models import Candle, Tick

class MarketProvider(ABC):
    @abstractmethod
    async def historical(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    async def latest_tick(self, symbol: str) -> Tick:
        raise NotImplementedError
