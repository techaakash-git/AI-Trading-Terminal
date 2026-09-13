"""LLM boundary: it narrates a supplied, deterministic analysis and never calculates it."""
from __future__ import annotations
import httpx
from ..core.config import settings

class AIProvider:
    async def explain(self, analysis: dict) -> dict:
        if settings.ai_provider != 'anthropic' or not all((settings.ai_base_url, settings.ai_auth_token, settings.ai_model)):
            return {'provider': 'disabled', 'status': 'unconfigured', 'text': 'AI narration is not configured. Deterministic analysis remains the source of truth.'}
        prompt = ('Explain the supplied analysis for an educational trading dashboard. Do not calculate, alter, repeat, or invent prices, indicators, entries, stops, targets, risk/reward, or backtest metrics. If discussing a number, only refer to values in the input. Do not give financial advice.\n\nDETERMINISTIC_INPUT:\n' + str(analysis))
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(settings.ai_base_url.rstrip('/') + '/messages', headers={'x-api-key': settings.ai_auth_token, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'}, json={'model': settings.ai_model, 'max_tokens': 500, 'messages': [{'role': 'user', 'content': prompt}]})
                response.raise_for_status(); body = response.json()
            text = ''.join(part.get('text', '') for part in body.get('content', []) if part.get('type') == 'text').strip()
            if not text: raise ValueError('Provider returned no text')
            return {'provider': 'anthropic', 'status': 'live', 'text': text}
        except (httpx.HTTPError, ValueError, TypeError):
            return {'provider': 'anthropic', 'status': 'degraded', 'text': 'AI narration is temporarily unavailable. Deterministic analysis remains available.'}

provider = AIProvider()
