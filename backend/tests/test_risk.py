from app.engine.risk import calculate_risk

def test_risk():
    r = calculate_risk(100, 2, 10000, 1)
    assert r["risk_amount"] == 100
    assert r["stop_distance"] == 4
    assert r["position_size"] == 25
