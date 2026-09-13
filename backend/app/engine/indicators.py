from __future__ import annotations
from typing import Sequence

def _validate(values, period):
    if period <= 0: raise ValueError('period must be positive')
    if not values: return

def sma(values: Sequence[float], period: int):
    _validate(values, period); out=[None]*len(values)
    if len(values)<period:return out
    window=sum(values[:period]); out[period-1]=window/period
    for i in range(period,len(values)):
        window += values[i]-values[i-period]; out[i]=window/period
    return out

def ema(values, period):
    _validate(values,period); out=[None]*len(values)
    if len(values)<period:return out
    prev=sum(values[:period])/period; out[period-1]=prev; a=2/(period+1)
    for i in range(period,len(values)): prev=(values[i]-prev)*a+prev; out[i]=prev
    return out

def rsi(values, period=14):
    _validate(values,period); out=[None]*len(values)
    if len(values)<=period:return out
    gains=[max(values[i]-values[i-1],0) for i in range(1,len(values))]
    losses=[max(values[i-1]-values[i],0) for i in range(1,len(values))]
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    def calc(): return 100.0 if al==0 else 100-100/(1+ag/al)
    out[period]=calc()
    for i in range(period,len(gains)):
        ag=((ag*(period-1))+gains[i])/period; al=((al*(period-1))+losses[i])/period; out[i+1]=calc()
    return out

def atr(highs,lows,closes,period=14):
    if not (len(highs)==len(lows)==len(closes)): raise ValueError('OHLC arrays must have equal length')
    tr=[highs[i]-lows[i] if i==0 else max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])) for i in range(len(closes))]
    return sma(tr,period)

def macd(values, fast=12, slow=26, signal=9):
    ef,es=ema(values,fast),ema(values,slow); line=[None if ef[i] is None or es[i] is None else ef[i]-es[i] for i in range(len(values))]
    compact=[x for x in line if x is not None]; sig=ema(compact,signal); signal_full=[None]*len(values); j=0
    for i,x in enumerate(line):
        if x is not None: signal_full[i]=sig[j]; j+=1
    hist=[None if line[i] is None or signal_full[i] is None else line[i]-signal_full[i] for i in range(len(values))]
    return {'macd':line,'signal':signal_full,'histogram':hist}

def support_resistance(candles, lookback=120, tolerance=0.003):
    c=candles[-lookback:]; highs=[x.high for x in c]; lows=[x.low for x in c]
    levels=[]
    for i in range(1,len(c)-1):
        if highs[i]>highs[i-1] and highs[i]>=highs[i+1]: levels.append(('resistance',highs[i]))
        if lows[i]<lows[i-1] and lows[i]<=lows[i+1]: levels.append(('support',lows[i]))
    clusters=[]
    for kind,p in sorted(levels,key=lambda x:x[1]):
        found=None
        for cl in clusters:
            if cl['kind']==kind and abs(p-cl['price'])/max(p,1)<tolerance: found=cl;break
        if found: found['prices'].append(p); found['price']=sum(found['prices'])/len(found['prices']); found['touches']+=1
        else: clusters.append({'kind':kind,'price':p,'touches':1,'prices':[p]})
    return [{'kind':x['kind'],'price':x['price'],'touches':x['touches']} for x in sorted(clusters,key=lambda x:-x['touches'])[:10]]

def calculate_indicators(candles):
    closes=[c.close for c in candles]; highs=[c.high for c in candles]; lows=[c.low for c in candles]
    s20=sma(closes,20); e20=ema(closes,20); e50=ema(closes,50); r=rsi(closes,14); a=atr(highs,lows,closes,14); m=macd(closes)
    trend='bullish' if e20[-1] and e50[-1] and e20[-1]>e50[-1] and closes[-1]>e20[-1] else 'bearish' if e20[-1] and e50[-1] and e20[-1]<e50[-1] and closes[-1]<e20[-1] else 'neutral'
    change24=None
    if len(closes)>1:
        n=min(len(closes)-1,24 if len(closes)>25 else len(closes)-1); change24=(closes[-1]/closes[-1-n]-1)*100
    return {'sma20':s20[-1],'ema20':e20[-1],'ema50':e50[-1],'rsi14':r[-1],'atr14':a[-1],'macd':m['macd'][-1],'macd_signal':m['signal'][-1],'macd_histogram':m['histogram'][-1],'trend':trend,'change24h_pct':change24,'support_resistance':support_resistance(candles)}
