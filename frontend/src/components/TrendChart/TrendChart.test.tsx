import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TrendChart } from "./TrendChart";

describe("TrendChart", () => {
  it("keeps a missing middle bucket as a visible chart gap", () => {
    render(
      <TrendChart
        points={[
          { date: "2026-01-01", value: 10 },
          { date: "2026-01-08", value: 20 },
          { date: "2026-01-15", value: null },
          { date: "2026-01-22", value: 30 },
          { date: "2026-01-29", value: 40 },
        ]}
        valueLabel="Sleep"
        emptyLabel="No history"
      />,
    );

    expect(screen.getByText("Sleep: latest value 40 · 1 missing period")).toBeVisible();
    expect(screen.getAllByTestId("trend-segment")).toHaveLength(2);
  });

  it("does not present an older value as latest when newest bucket is missing", () => {
    render(
      <TrendChart
        points={[
          { date: "2026-01-01", value: 60 },
          { date: "2026-01-08", value: null },
        ]}
        valueLabel="Recovery"
        emptyLabel="No history"
      />,
    );

    expect(screen.getByText("Recovery: latest value unavailable · 1 missing period")).toBeVisible();
    expect(screen.queryByText("Recovery: latest value 60")).not.toBeInTheDocument();
  });
});
