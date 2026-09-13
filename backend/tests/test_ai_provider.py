import asyncio
from app.ai.provider import provider

def test_disabled_provider_does_not_fabricate_narration():
    result = asyncio.run(provider.explain({'price': 100.0}))
    assert result['status'] == 'unconfigured'
    assert 'source of truth' in result['text']
