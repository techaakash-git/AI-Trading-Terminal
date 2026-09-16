from __future__ import annotations
import httpx
from datetime import datetime, timezone
from .base import MarketProvider
from ..models import Candle, Tick
from ..exceptions import RateLimitExceeded

class TwelveDataProvider(MarketProvider):
    name = 'twelve-data'

    def __init__(self, api_key: str, base_url: str = 'https://api.twelvedata.com'):
        self.api_key, self.base_url = api_key, base_url.rstrip('/')

    def _symbol(self, symbol: str) -> str:
        return 'BTC/USD' if symbol.upper() == 'BTCUSDT' else symbol.upper()

    async def historical(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        interval = {'1m':'1min','5m':'5min','15m':'15min','1h':'1h','4h':'4h','1d':'1day'}[timeframe]
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f'{self.base_url}/time_series', params={'symbol':self._symbol(symbol),'interval':interval,'outputsize':limit,'apikey':self.api_key})
            if r.status_code == 429:
                raise RateLimitExceeded(f'TwelveData 429: {r.text[:200]}')
            r.raise_for_status(); data = r.json()
        if data.get('status') == 'error': raise RuntimeError(data.get('message','Market provider error'))
        values = data.get('values', [])
        out=[]
        for x in reversed(values):
            ts=int(datetime.fromisoformat(x['datetime'].replace('Z','+00:00')).replace(tzinfo=timezone.utc).timestamp()) if 'T' in x['datetime'] else int(datetime.strptime(x['datetime'],'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp())
            out.append(Candle(time=ts,open=float(x['open']),high=float(x['high']),low=float(x['low']),close=float(x['close']),volume=float(x.get('volume',0) or 0)))
        return out

    async def latest_tick(self, symbol: str) -> Tick:
        candles = await self.historical(symbol,'1m',1)
        c=candles[-1]
        return Tick(symbol=symbol.upper(),price=c.close,timestamp=datetime.now(timezone.utc),volume=c.volume)
