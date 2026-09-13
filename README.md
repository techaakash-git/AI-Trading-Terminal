# AI Trading Platform — Production-Oriented Build

A BTC/BTCUSDT + XAUUSD analysis platform built around one non-negotiable rule: **Python computes every trading number; the LLM explains computed data and extracts validated strategy structure.**

## Current implementation
- Next.js/React/TypeScript trading terminal
- Lightweight Charts v5 native live chart; historical REST + WebSocket incremental updates
- BTCUSDT/XAUUSD and multiple timeframes
- deterministic SMA, EMA, RSI, MACD, ATR, support/resistance and trend
- deterministic ATR risk engine
- swing-based pattern detection
- strategy schema validation + no-lookahead EMA backtester
- health/market/analysis/backtest APIs
- Docker Compose with frontend/backend/PostgreSQL/Redis
- unit tests for indicators, strategy validation and no-lookahead backtesting

## Important
The repository is **not yet connected to a paid/real market-data provider, production database persistence, authentication, external news, or an LLM provider**. Demo market data is explicitly used so the application remains runnable without credentials. No real-money order execution is implemented.

## Run
```bash
cd backend
python -m venv .venv
# activate the venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000`.

## Test
```bash
cd backend
pytest -q
```

## Production roadmap
1. real provider adapters + historical storage + tick aggregation
2. PostgreSQL/TimescaleDB persistence and Redis pub/sub
3. news provider + deduplication
4. LangChain/LangGraph tools, state, persistence and AI narration
5. RAG/pgvector and multi-turn chat
6. strategy builder + richer backtester
7. alert engine and notifications
8. authentication/RBAC/rate limiting/audit logging
9. Vitest/Playwright/k6 and AI evaluations
10. OpenTelemetry/Prometheus/Sentry/Azure Monitor
11. GitHub Actions → ACR → Azure Container Apps + Key Vault

See `planning.md` and `AGENT_RULES.md` for the complete target architecture.
