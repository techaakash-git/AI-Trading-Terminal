import { z } from 'zod';

/**
 * Frontend validation layer (AGENT_RULES rule 8): external input crossing the
 * API and WebSocket boundary is validated with Zod before it is rendered.
 * Python remains the numerical source of truth; these schemas only guard the
 * client against malformed/unknown payloads.
 */

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
  reason: z.string().optional(),
});

const indicatorsSchema = z.object({
  rsi14: z.number().optional(),
  atr14: z.number().optional(),
  trend: z.string().optional(),
  trend_reason: z.string().optional(),
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