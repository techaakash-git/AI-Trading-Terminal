'use client';

import { useEffect, useState, type FormEvent } from 'react';
import {
  alertNotificationSchema,
  alertSchema,
  type Alert,
  type AlertFormInput,
  type Analysis,
} from '../lib/schemas';
import MarketChart from '../components/MarketChart';
import TradingViewWidget from '../components/TradingViewWidget';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const ALERT_CONDITION_OPTIONS: Array<{
  value: AlertFormInput['condition_type'];
  label: string;
}> = [
  { value: 'price', label: 'Price' },
  { value: 'rsi', label: 'RSI' },
  { value: 'macd_signal', label: 'MACD Signal' },
];

export interface AlertToast { alert_id?: string; symbol: string; message: string; }
export default function Home() {
  const [symbol, setSymbol] = useState('XAUUSD');
  const [alertConditionType, setAlertConditionType] = useState<AlertFormInput['condition_type']>('price');
  const [timeframe, setTimeframe] = useState('1h');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showAlertForm, setShowAlertForm] = useState(false);
  const [alertNotifications, setAlertNotifications] = useState<AlertToast[]>([]);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [chartEngine, setChartEngine] = useState<'lightweight' | 'tradingview'>('lightweight');

  // Sync theme with localStorage or system preference on mount
  useEffect(() => {
    const saved = localStorage.getItem('app-theme') as 'dark' | 'light' | null;
    if (saved === 'dark' || saved === 'light') {
      setTheme(saved);
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
      const initial = prefersLight ? 'light' : 'dark';
      setTheme(initial);
      document.documentElement.setAttribute('data-theme', initial);
    }
  }, []);

  const setThemeMode = (newTheme: 'dark' | 'light') => {
    setTheme(newTheme);
    localStorage.setItem('app-theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  // Sync chart engine with localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('app-chart-engine') as 'lightweight' | 'tradingview' | null;
    if (saved === 'lightweight' || saved === 'tradingview') {
      setChartEngine(saved);
    }
  }, []);

  const setChartEngineMode = (engine: 'lightweight' | 'tradingview') => {
    setChartEngine(engine);
    localStorage.setItem('app-chart-engine', engine);
  };

  // Overlay toggle state with localStorage persistence
  const [showEMA20, setShowEMA20] = useState(true);
  const [showEMA50, setShowEMA50] = useState(true);
  const [showEMA200, setShowEMA200] = useState(true);
  const [showSupportResistance, setShowSupportResistance] = useState(true);
  const [showPatterns, setShowPatterns] = useState(true);
  const [showVolume, setShowVolume] = useState(true);

  useEffect(() => {
    // Load overlay preferences from localStorage
    const savedEMA20 = localStorage.getItem('chart-show-ema-20');
    const savedEMA50 = localStorage.getItem('chart-show-ema-50');
    const savedEMA200 = localStorage.getItem('chart-show-ema-200');
    const savedSR = localStorage.getItem('chart-show-support-resistance');
    const savedPatterns = localStorage.getItem('chart-show-patterns');
    const savedVolume = localStorage.getItem('chart-show-volume');

    if (savedEMA20 !== null) setShowEMA20(JSON.parse(savedEMA20));
    if (savedEMA50 !== null) setShowEMA50(JSON.parse(savedEMA50));
    if (savedEMA200 !== null) setShowEMA200(JSON.parse(savedEMA200));
    if (savedSR !== null) setShowSupportResistance(JSON.parse(savedSR));
    const parsedPatterns = savedPatterns !== null ? JSON.parse(savedPatterns) : true;
    setShowPatterns(parsedPatterns);
    if (savedVolume !== null) setShowVolume(JSON.parse(savedVolume));
  }, []);

  const setShowEMA20State = (show: boolean) => {
    setShowEMA20(show);
    localStorage.setItem('chart-show-ema-20', JSON.stringify(show));
  };

  const setShowEMA50State = (show: boolean) => {
    setShowEMA50(show);
    localStorage.setItem('chart-show-ema-50', JSON.stringify(show));
  };

  const setShowEMA200State = (show: boolean) => {
    setShowEMA200(show);
    localStorage.setItem('chart-show-ema-200', JSON.stringify(show));
  };

  const setShowSupportResistanceState = (show: boolean) => {
    setShowSupportResistance(show);
    localStorage.setItem('chart-show-support-resistance', JSON.stringify(show));
  };

  const setShowPatternsState = (show: boolean) => {
    setShowPatterns(show);
    localStorage.setItem('chart-show-patterns', JSON.stringify(show));
  };

  const setShowVolumeState = (show: boolean) => {
    setShowVolume(show);
    localStorage.setItem('chart-show-volume', JSON.stringify(show));
  };

  // Indicator configuration for the dropdown
  // Removed unused indicatorConfigs array that was causing lint warnings.


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
      <header className="terminal-header">
        <div className="header-brand">
          <span className="brand-badge">TERMINAL</span>
          <div>
            <h1 className="brand-title">AI Trading Platform</h1>
            <span className="sub">BTCUSDT • XAUUSD • deterministic analytics</span>
          </div>
        </div>

        <div className="header-controls">
          <div className="control-group">
            <span className="control-label">Symbol</span>
            <div className="pills">
              {['BTCUSDT', 'XAUUSD'].map(item => (
                <button
                  className={symbol === item ? 'active' : ''}
                  onClick={() => setSymbol(item)}
                  key={item}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="header-divider-vertical" />

          <div className="control-group">
            <span className="control-label">Theme</span>
            <div className="theme-pills">
              <button
                type="button"
                className={theme === 'dark' ? 'active' : ''}
                onClick={() => setThemeMode('dark')}
                title="Switch to dark mode"
                aria-pressed={theme === 'dark'}
              >
                <span>🌙</span>
                <span>Dark</span>
              </button>
              <button
                type="button"
                className={theme === 'light' ? 'active' : ''}
                onClick={() => setThemeMode('light')}
                title="Switch to light mode"
                aria-pressed={theme === 'light'}
              >
                <span>☀️</span>
                <span>Light</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="header-separator-line" role="separator" aria-orientation="horizontal" />

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
        <select
          className="alert-condition-select"
          aria-label="Alert condition"
          value={alertConditionType}
          onChange={(event) => setAlertConditionType(event.target.value as AlertFormInput['condition_type'])}
        >
          {ALERT_CONDITION_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <button onClick={() => setShowAlertForm(true)}>+ Alert</button>
      </section>

      <section className="chart-section">
        <div className="chart-header">
          <span className="chart-title">Price Chart</span>
          <div className="pills chart-switch" role="group" aria-label="Chart engine">
            <button
              type="button"
              className={chartEngine === 'lightweight' ? 'active' : ''}
              onClick={() => setChartEngineMode('lightweight')}
              title="Render with Lightweight Charts v5"
              aria-pressed={chartEngine === 'lightweight'}
            >
              <span>📈</span>
              <span>Lightweight</span>
            </button>
            <button
              type="button"
              className={chartEngine === 'tradingview' ? 'active' : ''}
              onClick={() => setChartEngineMode('tradingview')}
              title="Embed the TradingView widget"
              aria-pressed={chartEngine === 'tradingview'}
            >
              <span>📊</span>
              <span>TradingView</span>
            </button>
          </div>
        </div>

        {/* Chart Overlay Controls */}
        <div className="chart-overlays" style={{ padding: '10px 14px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>Indicators:</span>
          <div className="dropdown" style={{ position: 'relative' }}>
            <button
              onClick={() => {
                const menu = document.getElementById('indicator-menu');
                if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
              }}
              style={{ fontSize: '12px', padding: '6px 10px' }}
            >
              Manage Indicators ▾
            </button>
            <div
              id="indicator-menu"
              onClick={(e) => e.stopPropagation()}
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                backgroundColor: 'var(--bg-color)',
                border: '1px solid var(--border-color)',
                padding: '8px',
                zIndex: 10,
                display: 'none',
                minWidth: '150px'
              }}
            >
              <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
                <input type="checkbox" checked={showEMA20} onChange={(e) => setShowEMA20State(e.target.checked)} />
                EMA 20
              </label>
              <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
                <input type="checkbox" checked={showEMA50} onChange={(e) => setShowEMA50State(e.target.checked)} />
                EMA 50
              </label>
              <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
                <input type="checkbox" checked={showEMA200} onChange={(e) => setShowEMA200State(e.target.checked)} />
                EMA 200
              </label>
              <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
                <input type="checkbox" checked={showSupportResistance} onChange={(e) => setShowSupportResistanceState(e.target.checked)} />
                S/R
              </label>
              <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px' }}>
                <input type="checkbox" checked={showPatterns} onChange={(e) => setShowPatternsState(e.target.checked)} />
                Patterns
              </label>
              <label style={{ display: 'block', fontSize: '12px' }}>
                <input type="checkbox" checked={showVolume} onChange={(e) => setShowVolumeState(e.target.checked)} />
                Volume
              </label>
            </div>
          </div>
        </div>

        <div className="chart-frame">
          {chartEngine === 'tradingview' ? (
            <TradingViewWidget
              symbol={symbol}
              timeframe={timeframe}
              theme={theme}
            />
          ) : (
            <MarketChart
              symbol={symbol}
              timeframe={timeframe}
              theme={theme}
              showEMA20={showEMA20}
              showEMA50={showEMA50}
              showEMA200={showEMA200}
              showSupportResistance={showSupportResistance}
              showPatterns={showPatterns}
              showVolume={showVolume}
            />
          )}
        </div>
      </section>

      <section className="stats">
        <Card t="Price" v={analysis ? Number(analysis.price).toFixed(2) : '—'} />
        <Card t="RSI 14" v={indicators.rsi14 ? indicators.rsi14.toFixed(2) : '—'} />
        <Card t="ATR 14" v={indicators.atr14 ? indicators.atr14.toFixed(2) : '—'} />
        <Card t="Trend" v={indicators.trend || '—'} />
        <Card t="Risk" v={risk.verdict || '—'} />
      </section>

      <section className="grid">
        <div className="panel">
          <div className="title">AI Analysis</div>
          {analysis ? (
            <>
              {/* Symbol & Timeframe header */}
              <div className="analysis-header">
                <strong>{symbol}</strong> · <span>{timeframe}</span>
              </div>

              {/* Trend rationale */}
              {indicators.trend_reason && (
                <div className="analysis-section">
                  <small className="analysis-section-label">Trend</small>
                  <p>{indicators.trend_reason}</p>
                </div>
              )}

              <div className={`verdict ${risk.verdict}`}>{risk.verdict?.toUpperCase()}</div>
              <p>Direction: <b>{risk.direction}</b></p>
              <p>Entry: <b>{risk.entry?.toFixed(2) || '—'}</b></p>
              <p>Stop: <b>{risk.stop_loss?.toFixed(2) || '—'}</b></p>
              <p>Target: <b>{risk.target?.toFixed(2) || '—'}</b></p>

              {/* Trade entry basis */}
              {risk.reason && (
                <div className="analysis-section">
                  <small className="analysis-section-label">Entry Basis</small>
                  <p>{risk.reason}</p>
                </div>
              )}

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

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
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