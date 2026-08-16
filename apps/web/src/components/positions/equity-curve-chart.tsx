"use client";

import { ColorType, createChart, LineSeries, type IChartApi } from "lightweight-charts";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

/** lightweight-charts renders to <canvas>, outside the CSS cascade, so
 * chrome uses the same resolved hex fallbacks as PriceChart. The equity
 * curve is a single magnitude-over-time series, not a polarity or
 * identity pair — it reuses the dataviz skill's already-validated
 * categorical-slot-1 blue from PriceChart's SMA20 rather than inventing a
 * new color for a one-series line. */
const CHROME = {
  light: { gridLine: "#e1e0d9", text: "#898781" },
  dark: { gridLine: "#2c2c2a", text: "#898781" },
};
const LINE_COLOR = "#2a78d6";

/** lightweight-charts requires strictly ascending, unique timestamps.
 * The backend's equity curve legitimately carries more than one point on
 * the same date whenever multiple positions close the same day — an
 * ordinary trading pattern, not malformed data — so points are collapsed
 * to one per date, keeping the last (final end-of-day) value, before
 * ever reaching the chart. */
function collapseToOnePerDate(points: [string, number][]): [string, number][] {
  const byDate = new Map<string, number>();
  for (const [date, value] of points) {
    byDate.set(date, value);
  }
  return [...byDate.entries()];
}

export function EquityCurveChart({ points }: { points: [string, number][] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const { resolvedTheme } = useTheme();
  const chrome = resolvedTheme === "dark" ? CHROME.dark : CHROME.light;

  useEffect(() => {
    const container = containerRef.current;
    const dedupedPoints = collapseToOnePerDate(points);
    if (!container || dedupedPoints.length === 0) return;

    const chart = createChart(container, {
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: chrome.text },
      grid: { vertLines: { color: chrome.gridLine }, horzLines: { color: chrome.gridLine } },
      width: container.clientWidth,
      height: 240,
    });
    chartRef.current = chart;

    const line = chart.addSeries(LineSeries, { color: LINE_COLOR, lineWidth: 2, title: "Equity" });
    line.setData(dedupedPoints.map(([date, value]) => ({ time: date, value })));
    chart.timeScale().fitContent();

    const resize = () => chart.applyOptions({ width: container.clientWidth });
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      chartRef.current = null;
    };
  }, [points, chrome]);

  if (points.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-muted-foreground">
        No equity curve yet — record and close a position first.
      </p>
    );
  }

  return <div ref={containerRef} data-testid="equity-curve-container" />;
}
