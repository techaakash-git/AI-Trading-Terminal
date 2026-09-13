from datetime import datetime, timezone
from app.market.aggregator import CandleAggregator
from app.market.models import Tick

def test_aggregator_opens_and_updates_same_bucket():
    a=CandleAggregator('1m')
    t1=Tick(symbol='BTCUSDT',price=100,timestamp=datetime.fromtimestamp(60,timezone.utc),volume=2)
    c,opened=a.update(t1)
    assert opened and c.open==100 and c.high==100 and c.low==100
    t2=Tick(symbol='BTCUSDT',price=105,timestamp=datetime.fromtimestamp(61,timezone.utc),volume=3)
    c,opened=a.update(t2)
    assert not opened and c.high==105 and c.close==105 and c.volume==5

def test_aggregator_rolls_on_new_bucket():
    a=CandleAggregator('1m')
    a.update(Tick(symbol='XAUUSD',price=10,timestamp=datetime.fromtimestamp(60,timezone.utc)))
    c,opened=a.update(Tick(symbol='XAUUSD',price=11,timestamp=datetime.fromtimestamp(120,timezone.utc)))
    assert opened and c.time==120 and c.open==11
    assert a.last_closed is not None
    assert a.last_closed.time == 60
    assert a.last_closed.close == 10
