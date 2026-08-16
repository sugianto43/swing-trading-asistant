import type { components } from "@/lib/api/schema";

export type SetupType = components["schemas"]["SetupType"];

export const SETUP_TYPES: SetupType[] = [
  "BREAKOUT",
  "PULLBACK_CONTINUATION",
  "MOMENTUM_CONTINUATION",
  "MA_RECLAIM",
  "VOLATILITY_SQUEEZE",
];
