import asyncio
from app.ai.agent import ChatRequest, run_chat
from app.market.providers.demo import DemoMarketProvider

def test_agent_turn_refreshes_deterministic_analysis_and_keeps_history():
    async def exercise():
        candles = await DemoMarketProvider().historical('BTCUSDT', '1h', 300)
        return await run_chat(ChatRequest(message='Summarize BTC', symbol='BTCUSDT'), candles)
    result = asyncio.run(exercise())
    assert result['analysis']['symbol'] == 'BTCUSDT'
    assert len(result['history']) == 2
    assert result['narration']['status'] == 'unconfigured'
