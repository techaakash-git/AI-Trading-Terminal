from app.alerts.service import AlertService

def test_alert_fires_once_per_upward_crossing():
    service = AlertService()
    alert = service.create_sync({'name': 'Test Alert', 'symbol': 'BTCUSDT', 'condition_value': 100, 'direction': 'up'})
    assert not service.evaluate_sync('BTCUSDT', 'price', 99)
    assert [item.id for item in service.evaluate_sync('BTCUSDT', 'price', 101)] == [alert.id]
    assert not service.evaluate_sync('BTCUSDT', 'price', 102)
