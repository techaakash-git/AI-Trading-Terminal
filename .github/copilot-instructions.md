# Copilot instructions

## Project invariants

- **Python is the numerical source of truth.** All trading numbers, indicators, risk values, pattern calculations, and backtest results must be computed by the backend engine. The AI layer may explain already-computed values or extract validated strategy structure; it must not invent or recalculate trading numbers.
- Keep deterministic trading logic testable and explicit. Do not execute arbitrary LLM-generated code.
- Demo market data must remain clearly identified as demo data. Do not present it as a real provider or add real-money order execution.
- Preserve the provider interfaces for market, news, and AI integrations. Select implementations through configuration rather than coupling application code to a concrete provider.
- Validate external input at the boundary: Pydantic models/services on the backend and Zod or typed validation on the frontend.
- Keep secrets out of browser-exposed code and environment variables.
- Read `AGENT_RULES.md` before architectural changes and `planning.md` before structural changes.

## Commands

Run backend commands from `backend\` with the project virtual environment activated:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the backend test suite and a focused test from `backend\`:

```powershell
pytest -q
pytest tests\test_indicators.py -q
pytest tests\test_backtesting.py -q
pytest -k "risk or strategy" -q
```

Run frontend commands from `frontend\`:

```powershell
npm install
npm run dev
npm run lint
npm run build
```

The frontend runs on `http://localhost:3000`; the API runs on `http://localhost:8000`.
For the complete local stack, from the repository root run:

```powershell
docker compose up --build
```

Database commands run from `backend\`:

```powershell
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

This is a modular monolith: one FastAPI backend, one Next.js 15 App Router frontend,
PostgreSQL, and Redis. Keep it modular rather than introducing services until scale
requires it.

### Backend flow

- `app/main.py` creates the FastAPI application and lifespan. Startup initializes the
  database and starts the market stream; shutdown stops the stream.
- `app/api/routes.py` is the single API router mounted at `/api`. It exposes health,
  market data/status, analysis, AI narration/chat, backtesting, strategies, alerts,
  news, and the market WebSocket.
- `app/market/` normalizes provider output into market models. `providers/base.py`
  defines the provider contract; demo and Twelve Data are adapters. The stream polls
  ticks, aggregates them into candles, persists them, and publishes updates through
  the realtime hub.
- `app/engine/` contains deterministic indicators, swing patterns, ATR-based risk,
  alerts, and the no-lookahead EMA backtester. Changes here should have explicit
  expected-value tests in `backend/tests/`.
- `app/ai/agent.py` calls the deterministic engine first (`calculate_indicators`,
  pattern detection, risk, and news), then passes the resulting analysis to the AI
  provider only for narration. Preserve this ordering and the typed request boundary.
- `app/strategies/service.py` validates strategy schemas and parses natural-language
  strategy intent; it must not turn free-form model output into executable code.
- `app/db/` contains SQLAlchemy async models/database setup and Alembic migrations.
  `app/news/` and `app/alerts/` are provider/service boundaries; news is disabled by
  default and alerts are currently in memory.

### Frontend and realtime flow

- `frontend/app/` uses the Next.js App Router. The terminal fetches historical candles
  and status over REST, then subscribes to
  `/api/ws/market/{symbol}?timeframe=1m` for live updates.
- Lightweight Charts receives initial history with `setData()` once. Apply subsequent
  candle messages with `series.update()`; never replace the entire chart dataset on
  every tick.
- Keep API URLs configurable through `NEXT_PUBLIC_API_URL`; do not put credentials in
  `NEXT_PUBLIC_*` variables.
- Supported symbols are currently `BTCUSDT` and `XAUUSD`; supported timeframes are
  `1m`, `5m`, `15m`, `1h`, `4h`, and `1d`. Keep backend validation and frontend
  controls aligned when adding values.

### Configuration and defaults

Configuration is loaded by `app/core/config.py` from `.env`. Copy
`backend\.env.example` for local settings. The default configuration is intentionally
credential-free: demo market data, disabled AI/news providers, PostgreSQL, Redis, and
`http://localhost:3000` CORS. Provider changes should be made through the corresponding
`MARKET_PROVIDER`, `AI_PROVIDER`, or `NEWS_PROVIDER` setting and their adapter.

## Repository-specific conventions

- Normalize symbols at API/provider boundaries (for example, uppercase `BTCUSDT`);
  keep canonical market data in the shared market models.
- Preserve incremental candle semantics: the aggregator emits an in-progress candle
  and tracks the last closed candle; persistence uses the symbol/timeframe/time key
  and updates the current candle rather than creating duplicates.
- Keep numerical calculations free of provider or HTTP concerns so they remain
  deterministic and independently testable.
- When changing a deterministic engine function, update or add the corresponding
  focused test and run that test before the broader suite.
- Use async SQLAlchemy/database and Redis interfaces consistently with the existing
  backend; do not introduce synchronous calls into request or stream paths.
- Treat provider status and the explicit demo source as part of the user-facing
  contract. Do not silently fall back to fake production-looking data.
- Keep the current API mounted under `/api` and preserve the WebSocket message shape
  expected by the frontend (`candle` updates and `heartbeat` messages).
- There is currently no frontend unit/e2e test suite; frontend verification is through
  the existing lint/build commands unless a test framework is intentionally added.
