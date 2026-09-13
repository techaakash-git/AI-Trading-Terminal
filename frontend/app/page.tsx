'use client';

import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, ColorType, createChart } from 'lightweight-charts';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
type StreamState = 'connecting' | 'live' | 'stale' | 'error';

export default function Home() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [streamState, setStreamState] = useState<StreamState>('connecting');
  const [source, setSource] = useState('');
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    let chart: ReturnType<typeof createChart> | undefined;
    let socket: WebSocket | undefined;
    async function connect() {
      try {
        setStreamState('connecting');
        const [historyResponse, statusResponse] = await Promise.all([
          fetch(`${API}/api/market/candles?symbol=${symbol}&timeframe=${timeframe}&limit=300`),
          fetch(`${API}/api/market/status`),
        ]);
        if (!historyResponse.ok || !chartRef.current) throw new Error('Market history unavailable');
        const history = await historyResponse.json();
        const status = await statusResponse.json();
        if (!alive) return;
        setSource(status.active_source || 'unknown');
        chart = createChart(chartRef.current, { autoSize: true, layout: { textColor: '#d5d9e2', background: { type: ColorType.Solid, color: '#0b0e13' } }, grid: { vertLines: { color: '#161b24' }, horzLines: { color: '#161b24' } }, rightPriceScale: { borderColor: '#252b36' }, timeScale: { borderColor: '#252b36' } });
        const series = chart.addSeries(CandlestickSeries, { upColor: '#16c784', downColor: '#ea3943', borderVisible: false, wickUpColor: '#16c784', wickDownColor: '#ea3943' });
        series.setData(history.candles);
        chart.timeScale().fitContent();
        socket = new WebSocket(`${API.replace(/^http/, 'ws')}/api/ws/market/${symbol}?timeframe=${timeframe}`);
        socket.onopen = () => setStreamState('live');
        socket.onerror = () => setStreamState('error');
        socket.onclose = () => alive && setStreamState('stale');
        socket.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'candle' && message.data) { series.update(message.data); setStreamState('live'); }
          else if (message.type === 'heartbeat') setStreamState('stale');
        };
      } catch { if (alive) setStreamState('error'); }
    }
    void connect();
    return () => { alive = false; socket?.close(); chart?.remove(); };
  }, [symbol, timeframe]);

  async function analyze() {
    setLoading(true);
    try { setAnalysis(await (await fetch(`${API}/api/analysis/${symbol}?timeframe=${timeframe}`)).json()); }
    finally { setLoading(false); }
  }
  const indicators = analysis?.indicators || {};
  const risk = analysis?.risk || {};
  return <main><header><div><b>AI Trading Terminal</b><span className="sub"> BTCUSDT • XAUUSD • deterministic analytics</span></div><div className="pills">{['BTCUSDT', 'XAUUSD'].map(item => <button className={symbol === item ? 'active' : ''} onClick={() => setSymbol(item)} key={item}>{item}</button>)}</div></header><section className="toolbar">{['1m', '5m', '15m', '1h', '4h', '1d'].map(item => <button className={timeframe === item ? 'active' : ''} onClick={() => setTimeframe(item)} key={item}>{item}</button>)}<button onClick={analyze}>{loading ? 'Analyzing…' : 'Analyze'}</button></section><section className="stats"><Card t="Price" v={analysis ? Number(analysis.price).toFixed(2) : '—'} /><Card t="RSI 14" v={indicators.rsi14 ? indicators.rsi14.toFixed(2) : '—'} /><Card t="ATR 14" v={indicators.atr14 ? indicators.atr14.toFixed(2) : '—'} /><Card t="Trend" v={indicators.trend || '—'} /><Card t="Risk" v={risk.verdict || '—'} /></section><section className="grid"><div className="panel chart"><div className="title">Live market chart <span className={streamState}>{streamState}</span>{source && <span className="source">{source}</span>}</div><div ref={chartRef} className="chartbox" />{streamState === 'stale' && <p className="muted">Market stream is stale; the last completed candle remains displayed.</p>}{streamState === 'error' && <p className="muted">Chart history is temporarily unavailable. Check the backend connection.</p>}</div><div className="panel"><div className="title">AI Analysis</div>{analysis ? <><div className={`verdict ${risk.verdict}`}>{risk.verdict?.toUpperCase()}</div><p>Direction: <b>{risk.direction}</b></p><p>Entry: <b>{risk.entry?.toFixed(2) || '—'}</b></p><p>Stop: <b>{risk.stop_loss?.toFixed(2) || '—'}</b></p><p>Target: <b>{risk.target?.toFixed(2) || '—'}</b></p><p>Patterns: {(analysis.patterns || []).map((pattern: any) => pattern.name).join(', ') || 'None detected'}</p><small>Python is the numerical source of truth. AI narration must only explain computed values.</small></> : <p className="muted">Press Analyze to run the deterministic pipeline.</p>}</div></section></main>;
}

function Card({ t, v }: { t: string; v: string }) { return <div className="card"><small>{t}</small><strong>{v}</strong></div>; }
