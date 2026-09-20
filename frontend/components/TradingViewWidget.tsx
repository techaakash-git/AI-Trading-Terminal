'use client';

import { useEffect, useRef } from 'react';

interface TradingViewWidgetProps {
  symbol: string;
  timeframe: string;
  theme: 'dark' | 'light';
}

declare global {
  interface Window {
    TradingView?: {
      widget: (config: Record<string, unknown>) => void;
    };
  }
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

const WIDGET_SRC = 'https://s3.tradingview.com/tv.js';

function loadTradingView(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.TradingView) {
      resolve();
      return;
    }

    const existing = document.querySelector(`script[src="${WIDGET_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('TradingView script failed to load')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = WIDGET_SRC;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('TradingView script failed to load'));
    document.head.appendChild(script);
  });
}

export default function TradingViewWidget({
  symbol,
  timeframe,
  theme,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    const container = containerRef.current;
    if (!container) return;

    const render = async () => {
      try {
        container.innerHTML = '';
        await loadTradingView();
        if (cancelled) return;

        const widgetId = `tv-widget-${symbol}-${timeframe}-${theme}`;
        const widgetRoot = document.createElement('div');
        widgetRoot.id = widgetId;
        widgetRoot.className = 'tradingview-widget-container__widget';
        widgetRoot.style.height = '100%';
        container.appendChild(widgetRoot);

        if (!window.TradingView?.widget) {
          throw new Error('TradingView widget API is unavailable');
        }

        window.TradingView.widget({
          container_id: widgetId,
          autosize: true,
          symbol: SYMBOL_MAP[symbol] ?? `OANDA:${symbol}`,
          interval: INTERVAL_MAP[timeframe] ?? '60',
          timezone: 'Etc/UTC',
          theme,
          style: '1',
          locale: 'en',
          allow_symbol_change: true,
          support_host: 'https://www.tradingview.com',
        });
      } catch (error) {
        if (!cancelled) {
          container.innerHTML =
            '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">' +
            'TradingView widget could not load. Switch back to Lightweight Charts.</div>';
        }
      }
    };

    render();

    return () => {
      cancelled = true;
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
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