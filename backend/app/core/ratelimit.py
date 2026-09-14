"""Shared rate-limit configuration (Phase 12 security baseline).

SlowAPI's limiter is created here so both ``app.main`` (for exception-handler
registration) and route modules (for ``@limiter.limit(...)`` decorators) can
import it without creating an import cycle through the FastAPI app object.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory limiter is per-process; swap for Redis storage in multi-worker
# deployments (storage_uri="redis://localhost:6379").
# Default: table stakes baseline; per-route decorators tighten sensitive ones.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    headers_enabled=True,
)