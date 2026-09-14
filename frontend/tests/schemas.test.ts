import { describe, it, expect } from 'vitest';
import {
  marketMessageSchema,
  alertNotificationSchema,
  alertSchema,
  analysisSchema,
  alertFormSchema,
} from '../lib/schemas';

describe('marketMessageSchema', () => {
  it('accepts a valid candle message', () => {
    const result = marketMessageSchema.safeParse({
      type: 'candle',
      data: { time: 1700000000, open: 1, high: 2, low: 0.5, close: 1.5 },
    });
    expect(result.success).toBe(true);
  });

  it('accepts a heartbeat message', () => {
    const result = marketMessageSchema.safeParse({ type: 'heartbeat' });
    expect(result.success).toBe(true);
  });

  it('rejects a message missing required fields', () => {
    const result = marketMessageSchema.safeParse({ type: 'candle', data: {} });
    expect(result.success).toBe(false);
  });

  it('rejects an unknown type', () => {
    const result = marketMessageSchema.safeParse({ type: 'foo' });
    expect(result.success).toBe(false);
  });
});

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
});