"""Typed agent boundary. Tools call deterministic application services only."""
from __future__ import annotations
from collections import defaultdict
from typing import Literal, TypedDict
from uuid import uuid4
from pydantic import BaseModel, Field
from ..engine.indicators import calculate_indicators, ema_series
from ..engine.patterns import detect_patterns
from ..engine.risk import calculate_risk
from ..news.service import get_news
from .provider import provider

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    symbol: Literal['BTCUSDT', 'XAUUSD'] = 'BTCUSDT'
    timeframe: Literal['1m', '5m', '15m', '1h', '4h', '1d'] = '1h'
    conversation_id: str | None = None

class AgentState(TypedDict):
    request: ChatRequest
    analysis: dict
    reply: dict

class ConversationStore:
    """Development fallback; replace with agent_messages persistence in production."""
    def __init__(self): self.messages: dict[str, list[dict]] = defaultdict(list)
    def append(self, conversation_id: str, role: str, content: str): self.messages[conversation_id].append({'role': role, 'content': content})
    def history(self, conversation_id: str) -> list[dict]: return self.messages[conversation_id][-20:]

conversations = ConversationStore()

async def analyze(candles, symbol):
    ind = calculate_indicators(candles)
    ema = ema_series(candles)
    patterns = detect_patterns(candles)
    risk = calculate_risk(candles[-1].close, ind['atr14'], trend=ind['trend'])
    news = await get_news(symbol)
    return {
        'symbol': symbol,
        'price': candles[-1].close,
        'indicators': ind,
        'ema': ema,
        'patterns': patterns,
        'risk': risk,
        'news': news,
    }

async def narrate(candles, symbol):
    analysis = await analyze(candles, symbol)
    return {'analysis': analysis, 'narration': await provider.explain(analysis)}

async def run_chat(request: ChatRequest, candles) -> dict:
    """A constrained agent turn: refresh data, calculate, then optionally narrate."""
    conversation_id = request.conversation_id or str(uuid4())
    conversations.append(conversation_id, 'user', request.message)
    result = await narrate(candles, request.symbol)
    reply = result['narration']
    conversations.append(conversation_id, 'assistant', reply['text'])
    return {'conversation_id': conversation_id, 'history': conversations.history(conversation_id), **result}
