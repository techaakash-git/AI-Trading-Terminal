def calculate_risk(price, atr_value, account_size=10000.0, risk_pct=1.0, trend='neutral'):
    if price<=0 or account_size<=0 or risk_pct<=0: raise ValueError('price, account_size and risk_pct must be positive')
    atr_value=atr_value or price*0.01; stop_distance=atr_value*2; risk_amount=account_size*risk_pct/100
    qty=risk_amount/stop_distance if stop_distance else 0
    if trend=='bullish':
        entry=price; stop=price-stop_distance; target=price+stop_distance*2; direction='long'
        reason=(f'Uptrend confirmed: enter long at {entry:.2f} (current price). '
                f'Stop-loss {stop:.2f} = {stop_distance:.2f} (2×ATR {atr_value:.2f}) below entry. '
                f'Target {target:.2f} = 2× stop-distance above entry -> risk-reward 1:2.')
    elif trend=='bearish':
        entry=price; stop=price+stop_distance; target=price-stop_distance*2; direction='short'
        reason=(f'Downtrend confirmed: enter short at {entry:.2f} (current price). '
                f'Stop-loss {stop:.2f} = {stop_distance:.2f} (2×ATR {atr_value:.2f}) above entry. '
                f'Target {target:.2f} = 2× stop-distance below entry -> risk-reward 1:2.')
    else:
        entry=price; stop=target=None; direction='none'
        reason=(f'Trend neutral at {price:.2f}; no directional entry. '
                f'ATR {atr_value:.2f} ({atr_value/price*100:.2f}% of price).')
    verdict='pass' if atr_value/price<0.05 and trend!='neutral' else 'reject'
    return {'verdict':verdict,'direction':direction,'account_size':account_size,'risk_pct':risk_pct,'risk_amount':risk_amount,'atr':atr_value,'stop_distance':stop_distance,'position_size':qty,'entry':entry,'stop_loss':stop,'target':target,'risk_reward':2.0 if direction!='none' else None,'reason':reason}
