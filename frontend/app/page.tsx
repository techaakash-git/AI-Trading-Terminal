'use client';

import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, ColorType, createChart } from 'lightweight-charts';
import {
  alertNotificationSchema,
  alertSchema,
  marketMessageSchema,
  type Alert,
  type AlertFormInput,
  type Analysis,
} from '../lib/schemas';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
type StreamState = 'connecting' | 'live' | 'stale' | 'error';
export interface AlertToast { alert_id?: string; symbol: string; message: string; }

export default function Home() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [streamState, setStreamState] = useState<StreamState>('connecting');
  const [source, setSource] = useState('');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [alertNotifications, setAlertNotifications] = useState<AlertToast[]>([]);
  const chartRef = useRef<HTMLDivElement>(null);

  // Load alerts
  useEffect(() => {
    async function loadAlerts() {
      try {
        const response = await fetch(`${API}/api/alerts?symbol=${symbol}`);
        if (response.ok) {
          const data = await response.json();
          setAlerts(data.alerts || []);
        }
      } catch (error) {
        console.error('Failed to load alerts:', error);
      }
    }
    loadAlerts();
  }, [symbol]);

  // WebSocket for alert notifications
  useEffect(() => {
    const alertSocket = new WebSocket(`${API.replace(/^http/, 'ws')}/api/ws/alerts`);

    alertSocket.onmessage = (event) => {
      const parsed = alertNotificationSchema.safeParse(JSON.parse(event.data));
      if (!parsed.success) return;
      const { data } = parsed.data;
      setAlertNotifications(prev => [data, ...prev.slice(0, 4)]); // Keep last 5
      // Show browser notification if permitted
      if (Notification.permission === 'granted') {
        new Notification(`Alert: ${data.symbol}`, {
          body: data.message,
          icon: '/favicon.ico'
        });
      }
    };

    return () => alertSocket.close();
  }, []);

  // Request notification permission
  useEffect(() => {
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

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
          const parsed = marketMessageSchema.safeParse(JSON.parse(event.data));
          if (!parsed.success) return;
          if (parsed.data.type === 'candle') { series.update(parsed.data.data); setStreamState('live'); }
          else if (parsed.data.type === 'heartbeat') setStreamState('stale');
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

  async function createAlert(alertData: AlertFormInput) {
    try {
      const response = await fetch(`${API}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...alertData, symbol })
      });
      if (response.ok) {
        const newAlert = alertSchema.parse(await response.json());
        setAlerts(prev => [newAlert, ...prev]);
        setShowAlertForm(false);
      }
    } catch (error) {
      console.error('Failed to create alert:', error);
    }
  }

  async function toggleAlert(alertId: string, enabled: boolean) {
    try {
      const response = await fetch(`${API}/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
      if (response.ok) {
        setAlerts(prev => prev.map(alert =>
          alert.id === alertId ? { ...alert, enabled } : alert
        ));
      }
    } catch (error) {
      console.error('Failed to toggle alert:', error);
    }
  }

  async function deleteAlert(alertId: string) {
    try {
      const response = await fetch(`${API}/api/alerts/${alertId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setAlerts(prev => prev.filter(alert => alert.id !== alertId));
      }
    } catch (error) {
      console.error('Failed to delete alert:', error);
    }
  }

  const indicators = analysis?.indicators || {};
  const risk = analysis?.risk || {};
  return (
    <main>
      <header>
        <div>
          <b>AI Trading Terminal</b>
          <span className="sub"> BTCUSDT • XAUUSD • deterministic analytics</span>
        </div>
        <div className="pills">
          {['BTCUSDT', 'XAUUSD'].map(item =>
            <button
              className={symbol === item ? 'active' : ''}
              onClick={() => setSymbol(item)}
              key={item}
            >
              {item}
            </button>
          )}
        </div>
      </header>

      {/* Alert Notifications */}
      {alertNotifications.length > 0 && (
        <section className="alert-notifications">
          {alertNotifications.map((notification, index) => (
            <div key={index} className="alert-notification">
              🚨 {notification.message}
            </div>
          ))}
        </section>
      )}

      <section className="toolbar">
        {['1m', '5m', '15m', '1h', '4h', '1d'].map(item =>
          <button
            className={timeframe === item ? 'active' : ''}
            onClick={() => setTimeframe(item)}
            key={item}
          >
            {item}
          </button>
        )}
        <button onClick={analyze}>{loading ? 'Analyzing…' : 'Analyze'}</button>
        <button onClick={() => setShowAlertForm(true)}>+ Alert</button>
      </section>

      <section className="stats">
        <Card t="Price" v={analysis ? Number(analysis.price).toFixed(2) : '—'} />
        <Card t="RSI 14" v={indicators.rsi14 ? indicators.rsi14.toFixed(2) : '—'} />
        <Card t="ATR 14" v={indicators.atr14 ? indicators.atr14.toFixed(2) : '—'} />
        <Card t="Trend" v={indicators.trend || '—'} />
        <Card t="Risk" v={risk.verdict || '—'} />
      </section>

      <section className="grid">
        <div className="panel chart">
          <div className="title">
            Live market chart
            <span className={streamState}>{streamState}</span>
            {source && <span className="source">{source}</span>}
          </div>
          <div ref={chartRef} className="chartbox" />
          {streamState === 'stale' && <p className="muted">Market stream is stale; the last completed candle remains displayed.</p>}
          {streamState === 'error' && <p className="muted">Chart history is temporarily unavailable. Check the backend connection.</p>}
        </div>

        <div className="panel">
          <div className="title">AI Analysis</div>
          {analysis ? (
            <>
              <div className={`verdict ${risk.verdict}`}>{risk.verdict?.toUpperCase()}</div>
              <p>Direction: <b>{risk.direction}</b></p>
              <p>Entry: <b>{risk.entry?.toFixed(2) || '—'}</b></p>
              <p>Stop: <b>{risk.stop_loss?.toFixed(2) || '—'}</b></p>
              <p>Target: <b>{risk.target?.toFixed(2) || '—'}</b></p>
              <p>Patterns: {(analysis.patterns || []).map((pattern) => pattern.name).join(', ') || 'None detected'}</p>
              <small>Python is the numerical source of truth. AI narration must only explain computed values.</small>
            </>
          ) : (
            <p className="muted">Press Analyze to run the deterministic pipeline.</p>
          )}
        </div>

        <div className="panel alerts">
          <div className="title">
            Alerts ({alerts.filter(a => a.enabled).length} active)
          </div>
          <div className="alert-list">
            {alerts.length === 0 ? (
              <p className="muted">No alerts configured for {symbol}</p>
            ) : (
              alerts.map(alert => (
                <AlertItem
                  key={alert.id}
                  alert={alert}
                  onToggle={toggleAlert}
                  onDelete={deleteAlert}
                />
              ))
            )}
          </div>
        </div>
      </section>

      {showAlertForm && (
        <AlertForm
          onSubmit={createAlert}
          onCancel={() => setShowAlertForm(false)}
          currentPrice={analysis?.price}
        />
      )}
    </main>
  );
}

function Card({ t, v }: { t: string; v: string }) {
  return (
    <div className="card">
      <small>{t}</small>
      <strong>{v}</strong>
    </div>
  );
}

function AlertItem({
  alert,
  onToggle,
  onDelete
}: {
  alert: Alert;
  onToggle: (id: string, enabled: boolean) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className={`alert-item ${alert.enabled ? 'enabled' : 'disabled'}`}>
      <div className="alert-info">
        <strong>{alert.name}</strong>
        <span className="alert-details">
          {alert.condition_type} {alert.direction} {alert.condition_value}
        </span>
        {alert.fired_count > 0 && (
          <span className="fired-count">Fired {alert.fired_count}x</span>
        )}
      </div>
      <div className="alert-actions">
        <button
          onClick={() => onToggle(alert.id, !alert.enabled)}
          className={alert.enabled ? 'disable' : 'enable'}
        >
          {alert.enabled ? '⏸️' : '▶️'}
        </button>
        <button onClick={() => onDelete(alert.id)} className="delete">
          🗑️
        </button>
      </div>
    </div>
  );
}

function AlertForm({
  onSubmit,
  onCancel,
  currentPrice
}: {
  onSubmit: (data: AlertFormInput) => void;
  onCancel: () => void;
  currentPrice?: number;
}) {
  const [formData, setFormData] = useState<AlertFormInput>({
    name: '',
    condition_type: 'price',
    condition_value: currentPrice || 0,
    direction: 'up',
    timeframe: '1h',
    notification_channels: ['browser']
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h3>Create Alert</h3>
          <button onClick={onCancel}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="alert-form">
          <div className="form-group">
            <label>Alert Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              placeholder="e.g., BTC Price Alert"
              required
            />
          </div>

          <div className="form-group">
            <label>Condition</label>
            <select
              value={formData.condition_type}
              onChange={(e) => setFormData({...formData, condition_type: e.target.value as AlertFormInput['condition_type']})}
            >
              <option value="price">Price</option>
              <option value="rsi">RSI</option>
              <option value="macd_signal">MACD Signal</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Direction</label>
              <select
                value={formData.direction}
                onChange={(e) => setFormData({...formData, direction: e.target.value as AlertFormInput['direction']})}
              >
                <option value="up">Above</option>
                <option value="down">Below</option>
              </select>
            </div>

            <div className="form-group">
              <label>Value</label>
              <input
                type="number"
                step="0.01"
                value={formData.condition_value}
                onChange={(e) => setFormData({...formData, condition_value: parseFloat(e.target.value)})}
                required
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="button" onClick={onCancel}>Cancel</button>
            <button type="submit">Create Alert</button>
          </div>
        </form>
      </div>
    </div>
  );
}
