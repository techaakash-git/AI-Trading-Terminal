from app.engine.indicators import sma,ema,rsi,calculate_indicators,ema_series
from app.market.models import Candle

def test_sma_hand_calculated(): assert sma([1,2,3,4],3)[-1]==3

def test_ema_seeded_sma(): assert ema([1,2,3],3)[-1]==2

def test_rsi_all_gains(): assert rsi([1,2,3,4,5],3)[3]==100

def _candles_up(n=210):
    """Monotonically rising candles — all indicator series fully defined."""
    return [Candle(time=i, open=100+i*0.1, high=101+i*0.1, low=99+i*0.1, close=100+i*0.1, volume=1)
            for i in range(n)]

def test_calculate_indicators_has_ema200():
    ind = calculate_indicators(_candles_up())
    assert 'ema200' in ind
    assert ind['ema200'] is not None

def test_calculate_indicators_has_support_resistance():
    ind = calculate_indicators(_candles_up())
    assert 'support_resistance' in ind
    assert isinstance(ind['support_resistance'], list)

def test_calculate_indicators_has_change24h_pct():
    ind = calculate_indicators(_candles_up())
    assert 'change24h_pct' in ind

def _candles_down(n=210):
    """Monotonically falling candles."""
    return [Candle(time=i, open=100-i*0.1, high=101-i*0.1, low=99-i*0.1, close=100-i*0.1, volume=1)
            for i in range(n)]

def test_trend_reason_bullish_mentions_ema_and_price():
    ind = calculate_indicators(_candles_up())
    assert ind['trend'] == 'bullish'
    assert 'EMA20' in ind['trend_reason'] and 'EMA50' in ind['trend_reason']
    assert 'bullish alignment' in ind['trend_reason']
    assert f"{ind['ema20']:.2f}" in ind['trend_reason']
    assert f"{ind['ema50']:.2f}" in ind['trend_reason']

def test_trend_reason_bearish_mentions_ema_and_price():
    ind = calculate_indicators(_candles_down())
    assert ind['trend'] == 'bearish'
    assert 'EMA20' in ind['trend_reason'] and 'EMA50' in ind['trend_reason']
    assert 'bearish alignment' in ind['trend_reason']
    assert f"{ind['ema20']:.2f}" in ind['trend_reason']

def test_trend_reason_neutral_for_range_bound():
    # Constant prices -> EMA20 == EMA50 == price, no directional alignment.
    candles = [Candle(time=i, open=100, high=101, low=99, close=100, volume=1)
               for i in range(210)]
    ind = calculate_indicators(candles)
    assert ind['trend'] == 'neutral'
    assert 'Neutral' in ind['trend_reason'] and 'not cleanly aligned' in ind['trend_reason']

def test_ema_series_returns_all_periods():
    ser = ema_series(_candles_up(), periods=(20, 50, 200))
    assert set(ser.keys()) == {20, 50, 200}
    assert len(ser[20]) == 191   # 210 - 20 + 1
    assert len(ser[200]) == 11   # 210 - 200 + 1

def test_ema_series_values_are_dicts():
    ser = ema_series(_candles_up(), periods=(20,))
    pt = ser[20][0]
    assert 'time' in pt and 'value' in pt
    assert isinstance(pt['time'], int)
    assert isinstance(pt['value'], float)

def test_ema_series_empty_candles():
    assert ema_series([], periods=(20,)) == {20: []}
