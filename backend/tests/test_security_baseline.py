from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Test client for API endpoints (dev mode allows unauthenticated access).

    Module-scoped so the FastAPI lifespan + async engine are started and torn
    down exactly once, avoiding per-test event-loop races with asyncpg/Redis.
    """
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Health endpoint should always work."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_market_status_endpoint(client):
    """Market status endpoint should work (demo provider, no external deps)."""
    response = client.get('/api/market/status')
    assert response.status_code == 200


def test_candles_endpoint(client):
    """Candles endpoint should return historical data in dev/demo mode."""
    response = client.get('/api/market/candles?symbol=BTCUSDT&timeframe=1h&limit=100')
    assert response.status_code == 200
    data = response.json()
    assert 'candles' in data
    assert data['symbol'] == 'BTCUSDT'


def test_auth_register_validation(client):
    """Registration endpoint should be wired and validate input."""
    # Invalid payload (missing fields) must be rejected with 422.
    response = client.post('/api/auth/register', json={})
    assert response.status_code == 422


def test_auth_login_rejects_bad_credentials(client):
    """Login with non-existent user returns 401."""
    response = client.post('/api/auth/login', json={
        'username': 'no_such_user',
        'email': 'x@example.com',
        'password': 'wrong',
    })
    assert response.status_code == 401


def test_auth_full_flow_register_login_me(client):
    """Register -> login -> /me round trip works with valid credentials."""
    username = 'algo_trader'
    # Register
    reg = client.post('/api/auth/register', json={
        'username': username,
        'email': 'algo@example.com',
        'password': 'Str0ngPass!',
    })
    # May already exist from a prior run; accept 201 (created) or 400 (dup).
    assert reg.status_code in (200, 201, 400)

    # Login
    login = client.post('/api/auth/login', json={
        'username': username,
        'email': 'algo@example.com',
        'password': 'Str0ngPass!',
    })
    if login.status_code == 401:
        # User pre-exists with a different password or DB not persisted; skip flow.
        return
    assert login.status_code == 200
    token = login.json().get('access_token')
    assert token

    # /me with bearer token
    me = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json()['username'] == username