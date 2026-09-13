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
