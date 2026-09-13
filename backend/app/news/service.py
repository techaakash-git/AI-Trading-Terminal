"""Informational news pipeline; it never changes deterministic trading output."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import re
import httpx
from ..core.config import settings

SYMBOL_TERMS = {'BTCUSDT': ('bitcoin', 'btc', 'crypto'), 'XAUUSD': ('gold', 'xau', 'bullion')}
BULLISH = {'gain', 'gains', 'rally', 'surge', 'bullish', 'approval', 'inflow', 'record'}
BEARISH = {'fall', 'falls', 'drop', 'plunge', 'bearish', 'outflow', 'hack', 'ban', 'selloff'}

def _score(text: str) -> str:
    words = re.findall(r"[a-z]+", text.lower())
    bull, bear = sum(w in BULLISH for w in words), sum(w in BEARISH for w in words)
    return 'bullish' if bull > bear else 'bearish' if bear > bull else 'neutral'

def _deduplicate(raw_items: list[dict]) -> list[dict]:
    seen, result = set(), []
    for raw in raw_items:
        title, url = str(raw.get('title') or '').strip(), str(raw.get('url') or '').strip()
        if not title or not url or title == '[Removed]': continue
        key = hashlib.sha256(f'{title}|{url}'.encode()).hexdigest()[:16]
        if key in seen: continue
        seen.add(key)
        result.append({'id': key, 'title': title, 'url': url, 'source': str((raw.get('source') or {}).get('name') or 'unknown'), 'published_at': raw.get('publishedAt') or datetime.now(timezone.utc).isoformat(), 'sentiment': _score(f"{title} {raw.get('description') or ''}")})
    return result

async def get_news(symbol: str, limit: int = 20) -> dict:
    symbol = symbol.upper(); empty = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    if settings.news_provider != 'newsapi' or not settings.news_api_key:
        return {'symbol': symbol, 'items': [], 'sentiment': empty, 'status': 'unconfigured', 'source': 'none'}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get('https://newsapi.org/v2/everything', params={'q': ' OR '.join(SYMBOL_TERMS.get(symbol, (symbol.lower(),))), 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': min(max(limit, 1), 100), 'apiKey': settings.news_api_key})
            response.raise_for_status(); payload = response.json()
        if payload.get('status') != 'ok': raise RuntimeError('NewsAPI error')
        items = _deduplicate(payload.get('articles', []))
        totals = {name: sum(item['sentiment'] == name for item in items) for name in empty}
        return {'symbol': symbol, 'items': items, 'sentiment': totals, 'status': 'live', 'source': 'newsapi'}
    except (httpx.HTTPError, RuntimeError, ValueError):
        return {'symbol': symbol, 'items': [], 'sentiment': empty, 'status': 'degraded', 'source': 'newsapi'}
