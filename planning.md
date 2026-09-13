# AI Trading Platform — Implementation Plan

Build BTC/BTCUSDT and XAUUSD analysis with realtime market data, professional charts,
technical indicators, risk, patterns, news, AI narration, LangGraph agent, RAG,
natural-language strategy builder, backtesting, alerts, chat, security, testing,
observability, Docker and Azure deployment.

Build order:
1. Foundation
2. Market data
3. Realtime charts
4. Deterministic engine
5. Patterns
6. News
7. AI narration
8. LangGraph agent
9. Strategy builder
10. Backtesting
11. Alerts
12. Security
13. Testing/observability
14. Docker/Azure

Realtime path:
Provider -> normalized tick -> candle aggregator -> WebSocket -> frontend state ->
Lightweight Charts series.update().
