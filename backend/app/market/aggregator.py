from __future__ import annotations
from dataclasses import dataclass
from .models import Candle, Tick

TIMEFRAME_SECONDS = {'1m':60,'5m':300,'15m':900,'1h':3600,'4h':14400,'1d':86400}

@dataclass
class CandleAggregator:
    timeframe: str
    current: Candle | None = None
    last_closed: Candle | None = None

    def __post_init__(self):
        if self.timeframe not in TIMEFRAME_SECONDS:
            raise ValueError(f'Unsupported timeframe: {self.timeframe}')

    def update(self, tick: Tick) -> tuple[Candle, bool]:
        step = TIMEFRAME_SECONDS[self.timeframe]
        bucket = (int(tick.timestamp.timestamp()) // step) * step
        if self.current is None or self.current.time != bucket:
            self.last_closed = self.current
            self.current = Candle(time=bucket, open=tick.price, high=tick.price, low=tick.price, close=tick.price, volume=tick.volume)
            return self.current, True
        c = self.current
        c.high = max(c.high, tick.price)
        c.low = min(c.low, tick.price)
        c.close = tick.price
        c.volume += tick.volume
        return c, False
