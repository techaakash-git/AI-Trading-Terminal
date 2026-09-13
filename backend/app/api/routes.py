import asyncio
import json
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from ..market.service import get_candles,get_tick, provider_status
from ..ai.agent import ChatRequest, analyze, narrate, run_chat
from ..engine.backtesting import backtest
from ..strategies.service import parse_strategy_intent, validate_strategy
from ..market.realtime import hub
from ..news.service import get_news
from ..alerts.service import alerts
router=APIRouter()
@router.get('/health')
async def health(): return {'status':'ok','service':'trading-api','version':'1.1.0', 'market': provider_status(), 'redis': hub.redis_available}
@router.get('/market/candles')
async def candles(symbol='BTCUSDT',timeframe='1h',limit:int=Query(300,ge=50,le=5000)):
 d=await get_candles(symbol,timeframe,limit); return {'symbol':symbol.upper(),'timeframe':timeframe,'candles':[c.model_dump() for c in d]}
@router.get('/market/tick/{symbol}')
async def tick(symbol): return (await get_tick(symbol)).model_dump(mode='json')
@router.get('/market/status')
async def market_status(): return {**provider_status(), 'redis': hub.redis_available}
@router.get('/news/{symbol}')
async def news(symbol: str, limit: int = Query(20, ge=1, le=100)):
    return await get_news(symbol, limit)
@router.get('/analysis/{symbol}')
async def analysis(symbol,timeframe='1h'): return await analyze(await get_candles(symbol,timeframe,300),symbol.upper())
@router.get('/ai/narrate/{symbol}')
async def ai_narration(symbol: str, timeframe: str = '1h'):
    return await narrate(await get_candles(symbol, timeframe, 300), symbol.upper())
@router.post('/ai/chat')
async def ai_chat(request: ChatRequest):
    return await run_chat(request, await get_candles(request.symbol, request.timeframe, 300))
@router.post('/backtests')
async def run_backtest(payload:dict):
    s=validate_strategy(payload.get('strategy',{})); d=await get_candles(payload.get('symbol','BTCUSDT'),payload.get('timeframe','1h'),min(int(payload.get('limit',1000)),5000)); return {'strategy':s.model_dump(),'result':backtest(d,s.model_dump())}
@router.post('/strategies/parse')
async def parse_strategy(payload: dict):
    return parse_strategy_intent(str(payload.get('text', '')), str(payload.get('name', 'Natural-language strategy'))).model_dump()
@router.post('/alerts')
async def create_alert(payload: dict): return alerts.create(payload).model_dump()
@router.post('/alerts/evaluate')
async def evaluate_alerts(payload: dict):
    return {'fired': [alert.model_dump() for alert in alerts.evaluate(str(payload['symbol']), str(payload.get('metric', 'price')), float(payload['value']))]}
@router.websocket('/ws/market/{symbol}')
async def market_ws(websocket:WebSocket,symbol:str,timeframe:str='1m'):
    await websocket.accept()
    pubsub = await hub.subscribe(symbol.upper(), timeframe)
    try:
        while True:
            message = await pubsub.get_message(timeout=10)
            if message and message.get('data'):
                await websocket.send_text(message['data'])
            else:
                await websocket.send_json({'type':'heartbeat','timestamp':__import__('time').time()})
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.close()
