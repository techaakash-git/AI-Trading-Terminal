import { z } from 'zod';
import type { CandlestickData, Time } from 'lightweight-charts';

/**
 * Frontend validation layer (AGENT_RULES rule 8): external input crossing the
 * API and WebSocket boundary is validated with Zod before it is rendered or
 * passed to the chart. Python remains the numerical source of truth; these
 * schemas only guard the client against malformed/unknown payloads.
 */

// ---- Market WebSocket payloads ----
// LWC Time = UTCTimestamp (number) | BusinessDay ({ year, month, day }) | string
const businessDaySchema = z.object({ year: z.number(), month: z.number(), day: z.number() });
const timeSchema = z.union([z.string(), z.number(), businessDaySchema]);

// We cast through `as unknown` because z.infer gives a wider type than LWC's
// Time branded alias, but the values are always compatible at runtime.
const candleSchema = z.object({
  time: timeSchema,
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
}) as z.ZodType<CandlestickData<Time>>;

export const marketMessageSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('candle'), data: candleSchema }),
  z.object({ type: z.literal('heartbeat') }),
]);

export type MarketMessage = z.infer<typeof marketMessageSchema>;

// ---- Alert realtime WebSocket payloads ----
export const alertNotificationSchema = z.object({
  type: z.literal('alert'),
  data: z.object({
    alert_id: z.string().optional(),
    symbol: z.string(),
    message: z.string(),
  }),
});

// ---- Alerts CRUD / list ----
export const alertSchema = z.object({
  id: z.string(),
  name: z.string(),
  symbol: z.string(),
  condition_type: z.string(),
  condition_value: z.number(),
  direction: z.string(),
  timeframe: z.string(),
  enabled: z.boolean(),
  notification_channels: z.array(z.string()),
  created_at: z.string(),
  fired_count: z.number(),
  last_fired_at: z.string().optional(),
});

export type Alert = z.infer<typeof alertSchema>;

// ---- Alert creation form input (validated before POST) ----
export const alertFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  condition_type: z.enum(['price', 'rsi', 'macd_signal']),
  condition_value: z.number(),
  direction: z.enum(['up', 'down']),
  timeframe: z.string(),
  notification_channels: z.array(z.string()).default(['browser']),
});

export type AlertFormInput = z.infer<typeof alertFormSchema>;

// ---- Analysis response from /api/analysis/{symbol} ----
// Fields are optional because individual sections can be absent; extras are
// tolerated so a forward-additive backend never breaks the client.
const riskSchema = z.object({
  verdict: z.string().optional(),
  direction: z.string().optional(),
  entry: z.number().optional(),
  stop_loss: z.number().optional(),
  target: z.number().optional(),
});

const indicatorsSchema = z.object({
  rsi14: z.number().optional(),
  atr14: z.number().optional(),
  trend: z.string().optional(),
});

export const analysisSchema = z
  .object({
    price: z.number().optional(),
    indicators: indicatorsSchema.optional(),
    risk: riskSchema.optional(),
    patterns: z.array(z.object({ name: z.string() })).optional(),
  })
  .passthrough();

export type Analysis = z.infer<typeof analysisSchema>;