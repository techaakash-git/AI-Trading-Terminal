from app.engine.risk import calculate_risk

def test_risk():
    r = calculate_risk(100, 2, 10000, 1)
    assert r["risk_amount"] == 100
    assert r["stop_distance"] == 4
    assert r["position_size"] == 25

def test_risk_bullish_reason_makes_long():
    r = calculate_risk(100, 2, 10000, 1, trend='bullish')
    assert r['direction'] == 'long'
    assert r['entry'] == 100 and r['stop_loss'] == 96 and r['target'] == 108
    assert 'long' in r['reason'] and 'risk-reward 1:2' in r['reason']
    assert '100.00' in r['reason']

def test_risk_bearish_reason_makes_short():
    r = calculate_risk(100, 2, 10000, 1, trend='bearish')
    assert r['direction'] == 'short'
    assert r['entry'] == 100 and r['stop_loss'] == 104 and r['target'] == 92
    assert 'short' in r['reason'] and 'risk-reward 1:2' in r['reason']

def test_risk_neutral_no_directional_entry():
    r = calculate_risk(100, 2, 10000, 1, trend='neutral')
    assert r['direction'] == 'none'
    # entry still surfaces the reference price; only directional stop/target are absent
    assert r['entry'] == 100 and r['stop_loss'] is None and r['target'] is None
    assert 'neutral' in r['reason'] and 'no directional entry' in r['reason']
