/** Trailing window for the instrument-detail price chart. Price bars and
 * indicator snapshots are trimmed to the same window so the two series
 * feeding PriceChart never disagree about the chart's date range. */
export const CHART_LOOKBACK_DAYS = 180;
