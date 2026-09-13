from __future__ import annotations

def _swings(candles, order=2):
    highs=[]; lows=[]
    for i in range(order,len(candles)-order):
        h=candles[i].high;l=candles[i].low
        if h>=max(x.high for x in candles[i-order:i+order+1]): highs.append((i,h))
        if l<=min(x.low for x in candles[i-order:i+order+1]): lows.append((i,l))
    return highs,lows

def detect_patterns(candles):
    if len(candles)<20:return []
    highs,lows=_swings(candles)
    out=[]
    if len(highs)>=3:
        a,b,c=highs[-3:]
        if abs(a[1]-c[1])/max(a[1],1)<0.02 and b[1]>a[1]*1.015: out.append({'name':'Head & Shoulders','direction':'bearish','confidence':0.78})
        elif abs(a[1]-b[1])/max(a[1],1)<0.015 and abs(b[1]-c[1])/max(b[1],1)<0.015: out.append({'name':'Triple Top','direction':'bearish','confidence':0.68})
    if len(lows)>=3:
        a,b,c=lows[-3:]
        if abs(a[1]-c[1])/max(a[1],1)<0.02 and b[1]<a[1]*0.985: out.append({'name':'Inverse Head & Shoulders','direction':'bullish','confidence':0.78})
        elif abs(a[1]-b[1])/max(a[1],1)<0.015 and abs(b[1]-c[1])/max(b[1],1)<0.015: out.append({'name':'Triple Bottom','direction':'bullish','confidence':0.68})
    return out
