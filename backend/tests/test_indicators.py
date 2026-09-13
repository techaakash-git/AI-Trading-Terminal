from app.engine.indicators import sma,ema,rsi

def test_sma_hand_calculated(): assert sma([1,2,3,4],3)[-1]==3

def test_ema_seeded_sma(): assert ema([1,2,3],3)[-1]==2

def test_rsi_all_gains(): assert rsi([1,2,3,4,5],3)[3]==100
