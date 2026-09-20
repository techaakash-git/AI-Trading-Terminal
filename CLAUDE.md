# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core rule

**Python computes every trading number. The LLM only explains or narrates pre-computed data.** Never move calculations into the AI layer. See `AGENT_RULES.md` for the full list of invariants — read it before any architectural change. Read `planning.md` before making structural changes.

## Commands

**Backend**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload                     # runs on :8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev      # Next.js dev server on :3000
npm run build
npm run lint     # ESLint via next lint
```

**Full stack (Docker)**
```bash
docker compose up --build
```

**Tests**
```bash
cd backend
pytest -q                        # all tests
pytest tests/test_indicators.py  # single file
```

**DB migrations**
```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

The platform is a **modular monolith**: one FastAPI backend, one Next.js 15 frontend, PostgreSQL, and Redis — split only when scale requires it.

### Backend (`backend/app/`)

| Package | Role |
|---|---|
| `core/config.py` | Pydantic-settings; all config comes from `.env` |
| `api/routes.py` | Single `APIRouter` mounted at `/api`; all HTTP + WebSocket endpoints |
| `market/` | Provider interface (`providers/base.py`), demo + Twelve Data adapters, `stream.py` (started in lifespan), `realtime.py` (Redis pub/sub hub), `aggregator.py`, `service.py` |
| `engine/` | Deterministic, testable: `indicators.py` (SMA/EMA/RSI/MACD/ATR), `patterns.py` (swing detection), `risk.py` (ATR-based sizing), `backtesting.py` (no-lookahead EMA backtester) |
| `strategies/service.py` | Strategy schema validation; parses natural-language strategy intent |
| `ai/` | `agent.py` (analyze/narrate/chat — calls Python engine first, then LLM for narrative), `provider.py` (provider interface), `rag.py` |
| `news/service.py` | News provider (disabled by default) |
| `alerts/service.py` | In-memory alert engine |
| `db/` | SQLAlchemy 2 async models + `database.py` (`init_db` called in lifespan) |

App startup sequence (`main.py`): `init_db()` → `stream.start()` → serve → `stream.stop()`.

### Frontend (`frontend/app/`)

Next.js 15 App Router. Data fetching via TanStack Query v5. Charts via Lightweight Charts v5 — **use incremental WebSocket updates, never replace full chart data on each tick**. Input validation with Zod.

### Provider pattern

Market, news, and AI are all behind interfaces (`providers/base.py` style). The active provider is selected by env var (`MARKET_PROVIDER`, `AI_PROVIDER`, `NEWS_PROVIDER`). Default is `demo` / `disabled` — the app runs without any paid credentials.

### WebSocket flow

`/api/ws/market/{symbol}?timeframe=1m` → `realtime.hub` subscribes to a Redis channel → publishes incremental ticks; falls back to heartbeat every 10 s when idle.

## Environment variables (`.env`)

Copy `.env.example` to `.env`. Key settings:

| Var | Default | Notes |
|---|---|---|
| `MARKET_PROVIDER` | `demo` | `twelvedata` (primary) or `demo`; keyless `free-public` always backs the chain |
| `MARKET_API_KEY` | — | Twelve Data key (also `TWELVEDATA_API_KEY`) |
| `DATABASE_URL` | local asyncpg URL | PostgreSQL 16 |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `AI_PROVIDER` | `disabled` | Enable to activate LLM narration |
| `NEWS_PROVIDER` | `disabled` | |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |

## Testing approach

Tests live in `backend/tests/`. Every deterministic calculation (indicators, risk, backtesting, strategy validation) has a test with explicit expected values. Use `pytest-asyncio` for async tests. There is no frontend test suite yet (Vitest/Playwright are on the roadmap).

## What is not implemented yet

Real market-data provider persistence, authentication/RBAC, production LLM integration, news provider, Vitest/Playwright tests, and Azure deployment pipeline. See the roadmap in `README.md`.
