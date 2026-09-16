from app.engine.backtesting import backtest
from app.market.models import Candle

def test_no_lookahead_entry_is_next_candle():
 c=[Candle(time=i,open=10+i,high=11+i,low=9+i,close=10+i,volume=1) for i in range(80)]
 r=backtest(c,{'fast':2,'slow':3})
 assert all(t['entry_index']==t['signal_index']+1 for t in r['trades'])

def test_entry_filters_reduce_trades():
 # Create a crossover: fast MA (2) crosses slow MA (3)
 # Need enough candles for ATR(14)
 prices = [10]*15 + [20]*15
 c=[Candle(time=i,open=prices[i],high=prices[i]+1,low=prices[i]-1,close=prices[i],volume=1) for i in range(len(prices))]
 r1=backtest(c,{'fast':2,'slow':3})
 r2=backtest(c,{'fast':2,'slow':3, 'rsi_buy_below': 1})
 assert len(r1['trades']) > 0
 assert len(r2['trades']) == 0
