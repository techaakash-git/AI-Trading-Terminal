# Autonomous Coding Rules

1. Read `planning.md` before architectural changes.
2. Keep trading calculations deterministic and testable.
3. Never fake production market data; demo data must be explicitly labeled.
4. Python calculates; AI explains.
5. Never execute arbitrary LLM-generated code.
6. Use provider interfaces for market, news and AI.
7. Realtime charts use incremental updates rather than replacing all data on every tick.
8. Validate external input with Pydantic/Zod.
9. Test deterministic calculations with expected values.
10. Fix failures before continuing.
11. Keep secrets out of the browser.
12. Prefer a modular monolith until scale proves otherwise.
13. For live market data, the configured provider must always have precedence over public/free fallback providers; the fallback is a safety net, not the default source of truth.
14. XAUUSD and other live symbols must be sourced from the same trusted provider chain used by the app configuration. Do not silently degrade to demo or public gold endpoints when a valid configured provider exists.
15. Realtime candle updates must preserve time ordering. Never push a new candle with an older timestamp than the newest candle already on the chart; update only the latest bar or append strictly newer bars.
16. Lightweight Charts updates must be incremental (`series.update()` / append) and must never reassign the full history array on every tick unless the data set is explicitly reset for a new symbol/timeframe.
17. Any third-party widget loader (such as TradingView) must be mounted into a stable container, cleaned up safely, and never queried by stale DOM nodes after re-render or symbol changes.
18. If a widget or chart script fails to load, fail gracefully to a visible fallback message instead of leaving a dangling script or broken DOM reference.
19. Before shipping chart-provider or websocket changes, run the focused market/provider tests and the frontend production build to verify the live chart path still works.
