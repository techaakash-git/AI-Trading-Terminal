import asyncio
from app.ai.provider import provider
from app.core.config import settings

def test_disabled_provider_does_not_fabricate_narration():
    settings.ai_provider = 'disabled'  # isolate from live .env so unconfigured behavior is deterministic
    result = asyncio.run(provider.explain({'price': 100.0}))
    assert result['status'] == 'unconfigured'
    assert 'source of truth' in result['text']
