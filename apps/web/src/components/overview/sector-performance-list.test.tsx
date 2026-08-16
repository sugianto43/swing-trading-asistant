import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SectorPerformanceList } from "./sector-performance-list";

describe("SectorPerformanceList", () => {
  it("renders an explicit empty state rather than a blank list", () => {
    render(<SectorPerformanceList sectors={[]} />);
    expect(screen.getByText("No sector performance data for this date yet.")).toBeInTheDocument();
  });

  it("sorts sectors by return, best first", () => {
    render(
      <SectorPerformanceList
        sectors={[
          { sector: "Energy", instrument_count: 3, avg_return_pct: -1.5 },
          { sector: "Banking", instrument_count: 5, avg_return_pct: 2.1 },
        ]}
      />,
    );

    const names = screen.getAllByTitle(/Energy|Banking/).map((el) => el.textContent);
    expect(names).toEqual(["Banking", "Energy"]);
  });

  it("signs positive returns with a leading + and negative ones without", () => {
    render(
      <SectorPerformanceList
        sectors={[
          { sector: "Banking", instrument_count: 5, avg_return_pct: 2.1 },
          { sector: "Energy", instrument_count: 3, avg_return_pct: -1.5 },
        ]}
      />,
    );

    expect(screen.getByText("+2.10%")).toBeInTheDocument();
    expect(screen.getByText("-1.50%")).toBeInTheDocument();
  });

  it("renders zero-width bars without NaN/Infinity when every sector is flat", () => {
    // maxAbs would be 0 without the Math.max(..., 0.01) floor, making
    // width a 0/0 = NaN percentage — this locks in that guard.
    render(
      <SectorPerformanceList
        sectors={[{ sector: "Banking", instrument_count: 5, avg_return_pct: 0 }]}
      />,
    );

    const bar = document.querySelector('[style*="width"]');
    expect(bar).not.toBeNull();
    expect(bar?.getAttribute("style")).not.toMatch(/NaN|Infinity/);
    expect(screen.getByText("+0.00%")).toBeInTheDocument();
  });
});
