import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { IndicatorSnapshot } from "@/lib/queries/indicators";
import type { PriceBar } from "@/lib/queries/instruments";

const addSeriesSpy = vi.fn();
const setData = vi.fn();
const priceScale = vi.fn(() => ({ applyOptions: vi.fn() }));
const chart = {
  addSeries: vi.fn((...args: unknown[]) => {
    addSeriesSpy(...args);
    return { setData, priceScale };
  }),
  timeScale: () => ({ fitContent: vi.fn() }),
  applyOptions: vi.fn(),
  remove: vi.fn(),
};
const createChart = vi.fn().mockReturnValue(chart);

vi.mock("lightweight-charts", () => ({
  createChart: (...args: unknown[]) => createChart(...args),
  CandlestickSeries: "CandlestickSeries",
  HistogramSeries: "HistogramSeries",
  LineSeries: "LineSeries",
  ColorType: { Solid: "solid" },
}));

import { PriceChart } from "./price-chart";

function makeBar(overrides: Partial<PriceBar> = {}): PriceBar {
  return {
    trade_date: "2024-01-01",
    open: 100,
    high: 105,
    low: 99,
    close: 103,
    volume: 1_000_000,
    previous_close: null,
    change: null,
    change_percent: null,
    source: "fixture",
    quality_status: "VALID",
    quality_notes: null,
    ...overrides,
  };
}

function makeIndicator(overrides: Partial<IndicatorSnapshot> = {}): IndicatorSnapshot {
  return {
    trade_date: "2024-01-01",
    indicator_version: "v1",
    sma_20: null,
    sma_50: null,
    sma_200: null,
    ema_20: null,
    ema_50: null,
    rsi_14: null,
    atr_14: null,
    macd: null,
    macd_signal: null,
    macd_histogram: null,
    bb_upper: null,
    bb_middle: null,
    bb_lower: null,
    volume_sma_20: null,
    relative_volume: null,
    rolling_high_20: null,
    rolling_low_20: null,
    return_1d: null,
    volatility_20: null,
    ...overrides,
  };
}

const BARS = [
  makeBar({ trade_date: "2024-01-01", open: 100, high: 105, low: 99, close: 103 }),
  makeBar({ trade_date: "2024-01-02", open: 103, high: 106, low: 102, close: 104 }),
];

const INDICATORS = [makeIndicator({ trade_date: "2024-01-01", sma_20: 101, sma_50: null })];

describe("PriceChart", () => {
  it("renders an explicit empty state when there are no bars, without mounting a chart", () => {
    render(<PriceChart bars={[]} indicators={[]} />);

    expect(screen.getByText("No price history available for this instrument.")).toBeInTheDocument();
    expect(createChart).not.toHaveBeenCalled();
  });

  it("adds candlestick, volume, and both SMA series with chronologically-ordered data", () => {
    render(<PriceChart bars={BARS} indicators={INDICATORS} />);

    expect(createChart).toHaveBeenCalledTimes(1);
    expect(addSeriesSpy).toHaveBeenCalledWith("CandlestickSeries", expect.any(Object));
    expect(addSeriesSpy).toHaveBeenCalledWith("HistogramSeries", expect.any(Object));
    expect(addSeriesSpy).toHaveBeenCalledWith(
      "LineSeries",
      expect.objectContaining({ title: "SMA20" }),
    );
    expect(addSeriesSpy).toHaveBeenCalledWith(
      "LineSeries",
      expect.objectContaining({ title: "SMA50" }),
    );

    const candlestickCall = setData.mock.calls[0][0];
    expect(candlestickCall[0]).toMatchObject({ time: "2024-01-01", open: 100 });
  });

  it("filters out null indicator values rather than plotting a gap as zero", () => {
    render(<PriceChart bars={BARS} indicators={INDICATORS} />);

    // addSeries is called in a fixed order (candlestick, volume, sma20,
    // sma50) and every call returns the same mocked setData, so
    // setData's calls line up with that same order. sma_50 is null on
    // the only indicator row — that series must receive no points, not
    // a point with value 0 (which would be a fabricated value the
    // backend never computed).
    expect(addSeriesSpy.mock.calls[3][1]).toMatchObject({ title: "SMA50" });
    expect(setData.mock.calls[3][0]).toEqual([]);
  });

  it("disposes the chart on unmount", () => {
    const { unmount } = render(<PriceChart bars={BARS} indicators={INDICATORS} />);
    unmount();
    expect(chart.remove).toHaveBeenCalled();
  });
});
