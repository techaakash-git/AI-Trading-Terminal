@echo off
cd /d "C:\AakashDeep\Personal\Trading Agent\phase-10-backtesting\ai-trading-platform\backend"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000