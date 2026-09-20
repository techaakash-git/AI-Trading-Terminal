'use client';

import { useEffect, useRef } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type SeriesDefinition,
  type SeriesType,
  type DeepPartial,
  type ChartOptions,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type Time,
  type UTCTimestamp,
  type SeriesMarker,
  type CandlestickSeriesOptions,
  type LineSeriesOptions,
  type HistogramSeriesOptions,
} from 'lightweight-charts';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface MarketChartProps {
  symbol: string;
  timeframe: string;
  theme: 'dark' | 'light';
}

interface BackendSeries {
  type: SeriesType;
  data?: unknown[];
  options?: Record<string, unknown>;
  priceScale?: Record<string, unknown>;
  markers?: SeriesMarker<Time>[];
}

/** A "bar" arriving over the live WebSocket stream. */
interface StreamCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Lightweight Charts v5 candlestick chart.
 *
 * Python (the backend /api/chart/config endpoint) computes every number —
 * candles, EMAs, volume, pattern markers, S/R levels — and returns a render
 * config. This component only draws it. Live WebSocket candle updates are
 * applied incrementally with series.update(), never by re-fetching the whole
 * history, so the chart stays smooth while the stream is running.
 */
export default function MarketChart({ symbol, timeframe, theme }: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let disposed = false;
    let ws: WebSocket | null = null;

    async function mount() {
      const host = containerRef.current;
      if (!host || disposed) return;

      // 1. Fetch the pre-computed render config from the backend.
      const params = new URLSearchParams({
        symbol,
        timeframe,
        chart_type: 'candlestick',
        show_emas: 'true',
        show_volume: 'true',
        theme,
      });

      let config: { chart?: DeepPartial<ChartOptions>; series?: BackendSeries[] } | null = null;
      try {
        const response = await fetch(`${API}/api/chart/config?${params}`);
        if (!response.ok) throw new Error(`chart/config ${response.status}`);
        const body = await response.json();
        // Backend returns {"config": [{"chart": ..., "series": [...]}]}
        config = body?.config?.[0] ?? null;
        console.log('[MarketChart] config:', config);
      } catch (error) {
        console.error('[MarketChart] failed to load config:', error);
        return;
      }
      if (disposed || !config) return;

      // 2. Create the chart.
      await new Promise(resolve => requestAnimationFrame(resolve));
      const chart = createChart(host, {
        autoSize: true,
        ...(config.chart ?? {}),
      });
      if (disposed) {
        chart.remove();
        return;
      }
      chartRef.current = chart;

      // 3. Add each series from the backend config.
      const alive: { series: ISeriesApi<SeriesType>; type: BackendSeries['type'] }[] = [];
      for (const s of config.series ?? []) {
        let definition: SeriesDefinition<SeriesType> | null = null;
        let series: ISeriesApi<SeriesType> | null = null;

        if (s.type === 'Candlestick') {
          definition = CandlestickSeries;
          series = chart.addSeries(definition, s.options as DeepPartial<CandlestickSeriesOptions>);
          if (s.data?.length) series.setData(s.data as CandlestickData<Time>[]);
          if (s.markers?.length) createSeriesMarkers(series, s.markers as SeriesMarker<Time>[]);
        } else if (s.type === 'Line') {
          definition = LineSeries;
          series = chart.addSeries(definition, s.options as DeepPartial<LineSeriesOptions>);
          if (s.data?.length) series.setData(s.data as LineData<Time>[]);
        } else if (s.type === 'Histogram') {
          definition = HistogramSeries;
          series = chart.addSeries(definition, s.options as DeepPartial<HistogramSeriesOptions>);
          if (s.data?.length) series.setData(s.data as HistogramData<Time>[]);
          if (s.priceScale) series.priceScale().applyOptions(s.priceScale as never);
        }

        if (definition && series) alive.push({ series, type: s.type });
      }

      // Pin the right edge to "now".
      chart.timeScale().scrollToRealTime();

      // 4. Live updates: incremental ws -> series.update(), never a re-fetch.
      const wsUrl = API.replace(/^http/, 'ws');
      ws = new WebSocket(`${wsUrl}/api/ws/market/${symbol}?timeframe=${timeframe}`);
      ws.onmessage = (event) => {
        let message: { type?: string; data?: StreamCandle } | null = null;
        try {
          message = JSON.parse(event.data as string);
        } catch {
          return; // ignore malformed frames
        }
        if (message?.type !== 'candle' || !message.data) return; // heartbeat/ticks ignored

        const { time, open, high, low, close, volume } = message.data;
        const ts = time as UTCTimestamp;

        const candleSeries = alive.find((a) => a.type === 'Candlestick');
        if (candleSeries) candleSeries.series.update({ time: ts, open, high, low, close });

        const volumeSeries = alive.find((a) => a.type === 'Histogram');
        if (volumeSeries) {
          volumeSeries.series.update({
            time: ts,
            value: volume,
            color: close >= open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
          });
        }
      };
      ws.onerror = (event) => console.error('[MarketChart] WebSocket error:', event);
      ws.onopen = () => console.log('[MarketChart] WebSocket opened.');
      ws.onclose = () => console.log('[MarketChart] WebSocket closed.');
    }

    mount();

    return () => {
      disposed = true;
      ws?.close();
      chartRef.current?.remove();
      chartRef.current = null;
    };
  }, [symbol, timeframe, theme]);

  return <div className="market-chart" ref={containerRef} aria-label={`${symbol} ${timeframe} chart`} />;
}
