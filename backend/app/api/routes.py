import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from ..market.service import get_candles,get_tick, provider_status
from ..ai.agent import ChatRequest, analyze, narrate, run_chat
from ..engine.backtesting import backtest
from ..strategies.service import parse_strategy_intent, validate_strategy
from ..market.realtime import hub
from ..news.service import get_news
from ..alerts.service import alerts, AlertCreate, AlertUpdate
from ..db.database import get_db
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

# Alert Management Endpoints
@router.post('/alerts')
async def create_alert(payload: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Create a new alert."""
    try:
        alert = await alerts.create(payload, db)
        return alert.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/alerts')
async def get_alerts(
    symbol: str = Query(None, description="Filter by symbol"),
    enabled_only: bool = Query(False, description="Only return enabled alerts"),
    db: AsyncSession = Depends(get_db)
):
    """Get all alerts, optionally filtered by symbol."""
    alert_list = await alerts.get_all(db, symbol=symbol, enabled_only=enabled_only)
    return {'alerts': [alert.model_dump() for alert in alert_list]}

@router.get('/alerts/{alert_id}')
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific alert by ID."""
    alert = await alerts.get_by_id(alert_id, db)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.model_dump()

@router.patch('/alerts/{alert_id}')
async def update_alert(alert_id: str, payload: AlertUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing alert."""
    alert = await alerts.update(alert_id, payload, db)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.model_dump()

@router.delete('/alerts/{alert_id}')
async def delete_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an alert."""
    success = await alerts.delete(alert_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {'success': True, 'message': 'Alert deleted'}

@router.get('/alerts/history/all')
async def get_alert_history(
    alert_id: str = Query(None, description="Filter by alert ID"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get alert firing history."""
    history = await alerts.get_history(db, alert_id=alert_id, limit=limit)
    return {'history': history}

@router.post('/alerts/evaluate')
async def evaluate_alerts(payload: dict, db: AsyncSession = Depends(get_db)):
    """Manually evaluate alerts for testing."""
    fired = await alerts.evaluate(
        str(payload['symbol']),
        str(payload.get('condition_type', 'price')),
        float(payload['value']),
        db
    )
    return {'fired': [f.model_dump() for f in fired]}
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

@router.websocket('/ws/alerts')
async def alerts_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time alert notifications."""
    await websocket.accept()

    # Subscribe to Redis alert channel
    alert_pubsub = await hub.subscribe('ALERTS', 'notifications')

    try:
        await websocket.send_json({
            'type': 'connected',
            'message': 'Alert notifications connected',
            'timestamp': __import__('time').time()
        })

        while True:
            message = await alert_pubsub.get_message(timeout=10)
            if message and message.get('data'):
                try:
                    alert_data = json.loads(message['data'])
                    await websocket.send_json({
                        'type': 'alert',
                        'data': alert_data,
                        'timestamp': __import__('time').time()
                    })
                except json.JSONDecodeError:
                    pass
            else:
                # Send heartbeat
                await websocket.send_json({
                    'type': 'heartbeat',
                    'timestamp': __import__('time').time()
                })

    except WebSocketDisconnect:
        pass
    finally:
        await alert_pubsub.close()
