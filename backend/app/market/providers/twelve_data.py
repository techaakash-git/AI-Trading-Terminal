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
        sym = {
            'BTCUSDT': 'BTC/USD',
            'XAUUSD': 'XAU/USD',
            'XAGUSD': 'XAG/USD',
        }.get(symbol.upper())
        return sym if sym else symbol.upper()

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
            dt_raw = x['datetime']
            if 'T' in dt_raw:
                parsed = datetime.fromisoformat(dt_raw.replace('Z', '+00:00'))
            elif ' ' in dt_raw:
                # Twelve Data returns "YYYY-MM-DD HH:MM:SS" for intraday bars.
                fmt = '%Y-%m-%d %H:%M:%S.%f' if '.' in dt_raw else '%Y-%m-%d %H:%M:%S'
                parsed = datetime.strptime(dt_raw, fmt)
            else:
                parsed = datetime.strptime(dt_raw, '%Y-%m-%d')
            ts = int(parsed.replace(tzinfo=timezone.utc).timestamp())
            out.append(Candle(time=ts, open=float(x['open']), high=float(x['high']), low=float(x['low']), close=float(x['close']), volume=float(x.get('volume', 0) or 0)))
        return out

    async def latest_tick(self, symbol: str) -> Tick:
        # The /quote endpoint is a single credit per call (vs. a full
        # /time_series fetch), so ad-hoc ticks never burn the historical budget.
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f'{self.base_url}/quote', params={'symbol': self._symbol(symbol), 'apikey': self.api_key})
            if r.status_code == 429:
                raise RateLimitExceeded(f'TwelveData 429: {r.text[:200]}')
            r.raise_for_status()
            data = r.json()
        if data.get('status') == 'error':
            raise RuntimeError(data.get('message', 'Market provider error'))
        try:
            price = float(data['close'])
            ts = datetime.fromisoformat(data['datetime'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            volume = float(data.get('volume', 0) or 0)
        except (KeyError, ValueError) as exc:
            raise RuntimeError(f'TwelveData quote malformed for {symbol}: {exc}')
        return Tick(symbol=symbol.upper(), price=price, timestamp=ts, volume=volume)
