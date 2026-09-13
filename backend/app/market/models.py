from datetime import datetime
from pydantic import BaseModel

class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

class Tick(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    volume: float = 0.0
