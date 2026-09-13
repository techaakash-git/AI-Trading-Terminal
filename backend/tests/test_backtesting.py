from app.engine.backtesting import backtest
from app.market.models import Candle

def test_no_lookahead_entry_is_next_candle():
 c=[Candle(time=i,open=10+i,high=11+i,low=9+i,close=10+i,volume=1) for i in range(80)]
 r=backtest(c,{'fast':2,'slow':3})
 assert all(t['entry_index']==t['signal_index']+1 for t in r['trades'])
