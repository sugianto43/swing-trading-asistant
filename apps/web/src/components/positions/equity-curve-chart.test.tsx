import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const addSeriesSpy = vi.fn();
const setData = vi.fn();
const chart = {
  addSeries: vi.fn((...args: unknown[]) => {
    addSeriesSpy(...args);
    return { setData };
  }),
  timeScale: () => ({ fitContent: vi.fn() }),
  applyOptions: vi.fn(),
  remove: vi.fn(),
};
const createChart = vi.fn().mockReturnValue(chart);

vi.mock("lightweight-charts", () => ({
  createChart: (...args: unknown[]) => createChart(...args),
  LineSeries: "LineSeries",
  ColorType: { Solid: "solid" },
}));

import { EquityCurveChart } from "./equity-curve-chart";

describe("EquityCurveChart", () => {
  it("renders an explicit empty state when there are no points, without mounting a chart", () => {
    render(<EquityCurveChart points={[]} />);

    expect(
      screen.getByText("No equity curve yet — record and close a position first."),
    ).toBeInTheDocument();
    expect(createChart).not.toHaveBeenCalled();
  });

  it("plots the equity curve as a single line series", () => {
    render(
      <EquityCurveChart
        points={[
          ["2024-01-01", 100_000_000],
          ["2024-01-02", 101_500_000],
        ]}
      />,
    );

    expect(createChart).toHaveBeenCalledTimes(1);
    expect(addSeriesSpy).toHaveBeenCalledWith("LineSeries", expect.objectContaining({ title: "Equity" }));
    expect(setData.mock.calls[0][0]).toEqual([
      { time: "2024-01-01", value: 100_000_000 },
      { time: "2024-01-02", value: 101_500_000 },
    ]);
  });

  it("collapses same-date points to the last value, rather than crashing lightweight-charts' ascending-unique-time assertion", () => {
    // Two positions closing the same day is an ordinary trading pattern,
    // not malformed data — the backend's real equity_curve does this.
    // lightweight-charts requires strictly ascending, unique timestamps,
    // so a naive pass-through throws and takes down the whole page.
    render(
      <EquityCurveChart
        points={[
          ["2024-03-05", 99_500],
          ["2024-03-05", 199_000],
        ]}
      />,
    );

    expect(setData.mock.calls[0][0]).toEqual([{ time: "2024-03-05", value: 199_000 }]);
  });

  it("disposes the chart on unmount", () => {
    const { unmount } = render(<EquityCurveChart points={[["2024-01-01", 100]]} />);
    unmount();
    expect(chart.remove).toHaveBeenCalled();
  });
});
