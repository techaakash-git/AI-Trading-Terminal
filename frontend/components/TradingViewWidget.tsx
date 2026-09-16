'use client';

import { useEffect, useRef } from 'react';

interface TradingViewWidgetProps {
  symbol: string;
  timeframe: string;
  theme: 'dark' | 'light';
}

/** Symbol map to well-known TradingView tickers. */
const SYMBOL_MAP: Record<string, string> = {
  BTCUSDT: 'BINANCE:BTCUSDT',
  XAUUSD: 'OANDA:XAUUSD',
};

/** timeframe -> TradingView advanced-chart interval code. */
const INTERVAL_MAP: Record<string, string> = {
  '1m': '1',
  '5m': '5',
  '15m': '15',
  '1h': '60',
  '4h': '240',
  '1d': 'D',
};

const WIDGET_SRC = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';

/**
 * TradingView Advanced Chart embed widget.
 *
 * TradingView's loader reads the JSON config from the text content of the
 * injected `<script src="…embed-widget-advanced-chart.js">` tag that follows
 * the widget container div, so both must be re-created every time the
 * symbol/timeframe/theme changes. The previous instance (DOM node + its
 * loader bookkeeping) is removed so the overlay never stacks widgets.
 */
export default function TradingViewWidget({
  symbol,
  timeframe,
  theme,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Wipe any previous widget (including its DOM + loader bookkeeping).
    container.innerHTML = '';

    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'tradingview-widget-container__widget';
    widgetDiv.style.height = '100%';
    container.appendChild(widgetDiv);

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = WIDGET_SRC;
    script.text = JSON.stringify({
      autosize: true,
      symbol: SYMBOL_MAP[symbol] ?? `OANDA:${symbol}`,
      interval: INTERVAL_MAP[timeframe] ?? '60',
      timezone: 'Etc/UTC',
      theme,
      style: '1', // candlesticks
      locale: 'en',
      allow_symbol_change: true,
      support_host: 'https://www.tradingview.com',
    });
    script.onerror = () => {
      widgetDiv.innerHTML =
        '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">' +
        'TradingView widget could not load (are you offline?). Switch back to Lightweight Charts.</div>';
    };
    container.appendChild(script);

    return () => {
      container.innerHTML = '';
    };
  }, [symbol, timeframe, theme]);

  return (
    <div
      className="tradingview-widget-container"
      ref={containerRef}
      aria-label={`TradingView ${symbol} widget`}
    />
  );
}