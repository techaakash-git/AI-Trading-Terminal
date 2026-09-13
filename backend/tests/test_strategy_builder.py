from app.strategies.service import parse_strategy_intent

def test_natural_language_parser_returns_validated_declarative_schema():
    strategy = parse_strategy_intent('buy when RSI < 30 and price is above EMA 200, use a 2 ATR stop')
    assert strategy.rsi_buy_below == 30
    assert strategy.price_above_ema == 200
    assert strategy.stop_atr_multiple == 2
