import { describe, it, expect } from 'vitest';
import {
  alertNotificationSchema,
  alertSchema,
  analysisSchema,
  alertFormSchema,
} from '../lib/schemas';

describe('alertNotificationSchema', () => {
  it('accepts an alert notification payload', () => {
    const result = alertNotificationSchema.safeParse({
      type: 'alert',
      data: { alert_id: 'abc', symbol: 'BTCUSDT', message: 'crossed up 100' },
    });
    expect(result.success).toBe(true);
  });

  it('rejects missing symbol', () => {
    const result = alertNotificationSchema.safeParse({
      type: 'alert',
      data: { message: 'no symbol' },
    });
    expect(result.success).toBe(false);
  });
});

describe('alertSchema', () => {
  it('accepts a full alert object', () => {
    const result = alertSchema.safeParse({
      id: 'uuid-1',
      name: 'BTC Alert',
      symbol: 'BTCUSDT',
      condition_type: 'price',
      condition_value: 50000,
      direction: 'up',
      timeframe: '1h',
      enabled: true,
      notification_channels: ['browser'],
      created_at: '2026-09-13T10:00:00Z',
      fired_count: 0,
    });
    expect(result.success).toBe(true);
  });

  it('rejects an alert missing required id', () => {
    const result = alertSchema.safeParse({ name: 'BTC Alert', condition_type: 'price' });
    expect(result.success).toBe(false);
  });
});

describe('alertFormSchema', () => {
  it('accepts a valid form submission', () => {
    const result = alertFormSchema.safeParse({
      name: 'my alert',
      condition_type: 'price',
      condition_value: 100,
      direction: 'up',
      timeframe: '1h',
      notification_channels: ['browser'],
    });
    expect(result.success).toBe(true);
  });

  it('rejects an empty name', () => {
    const result = alertFormSchema.safeParse({
      name: '',
      condition_type: 'price',
      condition_value: 100,
      direction: 'up',
    });
    expect(result.success).toBe(false);
  });

  it('rejects an invalid condition_type', () => {
    const result = alertFormSchema.safeParse({
      name: 'x',
      condition_type: 'bogus',
      condition_value: 100,
      direction: 'up',
    });
    expect(result.success).toBe(false);
  });
});

describe('analysisSchema', () => {
  it('accepts a minimal analysis payload', () => {
    const result = analysisSchema.safeParse({ price: 100, risk: { verdict: 'long' } });
    expect(result.success).toBe(true);
  });

  it('tolerates forward-additive extra fields', () => {
    const result = analysisSchema.safeParse({ price: 100, some_future_field: 'ignored' });
    expect(result.success).toBe(true);
  });

  it('rejects non-object payload', () => {
    expect(analysisSchema.safeParse('hello').success).toBe(false);
    expect(analysisSchema.safeParse(42).success).toBe(false);
  });

  it('accepts the enhanced analysis payload (symbol, trend_reason, risk.reason)', () => {
    const result = analysisSchema.safeParse({
      symbol: 'XAUUSD',
      price: 4570.97,
      indicators: {
        rsi14: 54.2,
        atr14: 12.5,
        trend: 'bullish',
        trend_reason: 'Uptrend: EMA20 (4571.00) > EMA50 (4550.00) and price (4570.97) is above EMA20 -> bullish alignment.',
      },
      risk: {
        verdict: 'pass',
        direction: 'long',
        entry: 4570.97,
        stop_loss: 4545.97,
        target: 4620.97,
        reason: 'Uptrend confirmed: enter long at 4570.97 (current price). Stop-loss 4545.97 = 25.00 (2×ATR 12.50) below entry. Target 4620.97 = 2× stop-distance above entry -> risk-reward 1:2.',
      },
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.indicators?.trend_reason).toContain('EMA20');
      expect(result.data.risk?.reason).toContain('risk-reward');
      expect(result.data.symbol).toBe('XAUUSD');
    }
  });
});