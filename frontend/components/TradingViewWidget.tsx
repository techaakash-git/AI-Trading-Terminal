'use client';

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

/** timeframe -> TradingView interval code. */
const INTERVAL_MAP: Record<string, string> = {
  '1m': '1',
  '5m': '5',
  '15m': '15',
  '1h': '60',
  '4h': '240',
  '1d': '1D',
};

export default function TradingViewWidget({
  symbol,
  timeframe,
  theme,
}: TradingViewWidgetProps) {
  const activeSymbol = SYMBOL_MAP[symbol] ?? `OANDA:${symbol}`;
  const interval = INTERVAL_MAP[timeframe] ?? '60';
  const widgetUrl = new URL('https://www.tradingview.com/widgetembed/');
  widgetUrl.searchParams.set('symbol', activeSymbol);
  widgetUrl.searchParams.set('interval', interval);
  widgetUrl.searchParams.set('theme', theme);
  widgetUrl.searchParams.set('style', '1');
  widgetUrl.searchParams.set('locale', 'en');
  widgetUrl.searchParams.set('allow_symbol_change', 'true');
  widgetUrl.searchParams.set('toolbarbg', theme === 'dark' ? '#0f172a' : '#f8fafc');
  widgetUrl.searchParams.set('saveimage', 'true');
  widgetUrl.searchParams.set('details', '1');
  widgetUrl.searchParams.set('studies', '[]');

  return (
    <div className="tradingview-widget-container" aria-label={`TradingView ${symbol} widget`}>
      <iframe
        title={`TradingView ${symbol} widget`}
        src={widgetUrl.toString()}
        style={{ width: '100%', height: '100%', border: 'none' }}
        loading="lazy"
        sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
      />
    </div>
  );
}