"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
} from "lightweight-charts";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

import type { IndicatorSnapshot } from "@/lib/queries/indicators";
import type { PriceBar } from "@/lib/queries/instruments";

/**
 * Colors are the dataviz skill's own validated defaults, not invented:
 * up/down is a genuine polarity signal (status good/critical), and the
 * two SMA lines are an identity pair (categorical slots 1/2, blue/orange
 * — the documented adjacent pair with CVD ΔE 9.1 light / 8.4 dark,
 * clear of the ≥8 target). shadcn's own --chart-* tokens are pure
 * grayscale (neutral preset) and don't carry these two semantics.
 *
 * lightweight-charts renders to <canvas>, outside the CSS cascade — it
 * cannot resolve `var(--foo)` or `color-mix()`, only literal colors, so
 * chrome (gridlines/text) uses the dataviz skill's own resolved hex
 * fallbacks per mode rather than shadcn's CSS custom properties.
 */
const CHROME = {
  light: { gridLine: "#e1e0d9", text: "#898781" },
  dark: { gridLine: "#2c2c2a", text: "#898781" },
};

const SERIES_COLORS = {
  up: "#0ca30c",
  down: "#d03b3b",
  sma20: "#2a78d6",
  sma50: "#eb6834",
};

export function PriceChart({
  bars,
  indicators,
}: {
  bars: PriceBar[];
  indicators: IndicatorSnapshot[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const { resolvedTheme } = useTheme();
  const chrome = resolvedTheme === "dark" ? CHROME.dark : CHROME.light;

  useEffect(() => {
    const container = containerRef.current;
    if (!container || bars.length === 0) return;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: chrome.text,
      },
      grid: {
        vertLines: { color: chrome.gridLine },
        horzLines: { color: chrome.gridLine },
      },
      width: container.clientWidth,
      height: 400,
    });
    chartRef.current = chart;

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: SERIES_COLORS.up,
      downColor: SERIES_COLORS.down,
      borderVisible: false,
      wickUpColor: SERIES_COLORS.up,
      wickDownColor: SERIES_COLORS.down,
    });
    candles.setData(
      bars.map((bar) => ({
        time: bar.trade_date,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      })),
    );

    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volume.setData(
      bars.map((bar) => ({
        time: bar.trade_date,
        value: bar.volume,
        color: bar.close >= bar.open ? `${SERIES_COLORS.up}80` : `${SERIES_COLORS.down}80`,
      })),
    );

    const sma20 = chart.addSeries(LineSeries, {
      color: SERIES_COLORS.sma20,
      lineWidth: 2,
      title: "SMA20",
    });
    sma20.setData(
      indicators
        .filter((snap) => snap.sma_20 !== null)
        .map((snap) => ({ time: snap.trade_date, value: snap.sma_20 as number })),
    );

    const sma50 = chart.addSeries(LineSeries, {
      color: SERIES_COLORS.sma50,
      lineWidth: 2,
      title: "SMA50",
    });
    sma50.setData(
      indicators
        .filter((snap) => snap.sma_50 !== null)
        .map((snap) => ({ time: snap.trade_date, value: snap.sma_50 as number })),
    );

    chart.timeScale().fitContent();

    const resize = () => chart.applyOptions({ width: container.clientWidth });
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, indicators, chrome]);

  if (bars.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-muted-foreground">
        No price history available for this instrument.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center gap-4 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-3" style={{ backgroundColor: SERIES_COLORS.sma20 }} />
          SMA20
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-3" style={{ backgroundColor: SERIES_COLORS.sma50 }} />
          SMA50
        </span>
      </div>
      <div ref={containerRef} data-testid="price-chart-container" />
    </div>
  );
}
