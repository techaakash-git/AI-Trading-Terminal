"""Validated declarative strategies. Generated Python is never accepted or executed."""
from __future__ import annotations
import re
from pydantic import BaseModel, Field, model_validator

class Strategy(BaseModel):
    name: str = Field(default='EMA Crossover', min_length=1, max_length=100)
    fast: int = Field(20, ge=2, le=200)
    slow: int = Field(50, ge=3, le=400)
    risk_pct: float = Field(1, gt=0, le=5)
    rsi_buy_below: float | None = Field(default=None, gt=0, lt=100)
    price_above_ema: int | None = Field(default=None, ge=2, le=400)
    stop_atr_multiple: float = Field(default=2, gt=0, le=10)

    @model_validator(mode='after')
    def periods_are_valid(self):
        if self.fast >= self.slow: raise ValueError('fast period must be less than slow period')
        return self

def validate_strategy(data): return Strategy.model_validate(data)

def parse_strategy_intent(text: str, name: str = 'Natural-language strategy') -> Strategy:
    """Small deterministic parser used when an LLM structured-output provider is unavailable."""
    lower = text.lower(); values: dict = {'name': name}
    rsi = re.search(r'rsi\s*(?:<|below)\s*(\d+(?:\.\d+)?)', lower)
    above = re.search(r'(?:above|over)\s*ema\s*(\d+)', lower)
    stop = re.search(r'(\d+(?:\.\d+)?)\s*atr\s*(?:stop|loss)', lower)
    if rsi: values['rsi_buy_below'] = float(rsi.group(1))
    if above: values['price_above_ema'] = int(above.group(1))
    if stop: values['stop_atr_multiple'] = float(stop.group(1))
    return validate_strategy(values)
