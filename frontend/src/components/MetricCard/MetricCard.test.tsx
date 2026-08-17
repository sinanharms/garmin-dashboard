import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MetricCard } from "./MetricCard";
import { StatusBadge } from "../StatusBadge/StatusBadge";
import { TrendChart } from "../TrendChart/TrendChart";

describe("MetricCard", () => {
  it("shows summary and expands detail through an accessible control", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();

    render(
      <MetricCard
        title="Training load"
        value="60"
        expanded={false}
        onToggle={onToggle}
        detail={<p>History</p>}
      />,
    );

    expect(screen.getByText("60")).toBeVisible();
    expect(screen.queryByText("History")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /training load/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );

    await user.click(screen.getByRole("button", { name: /training load/i }));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("renders expanded detail while preserving the summary", () => {
    render(
      <MetricCard
        title="Training load"
        value="60"
        expanded
        onToggle={vi.fn()}
        detail={<p>History</p>}
      />,
    );

    expect(screen.getByText("60")).toBeVisible();
    expect(screen.getByText("History")).toBeVisible();
    expect(screen.getByRole("button", { name: /training load/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });
});

describe("StatusBadge and TrendChart", () => {
  it("communicates unavailable status with text", () => {
    render(<StatusBadge status="missing" label="Sleep unavailable" />);

    expect(screen.getByText("Sleep unavailable")).toBeVisible();
  });

  it("exposes an empty chart message", () => {
    render(<TrendChart points={[]} valueLabel="Training load" emptyLabel="No history" />);

    expect(screen.getByText("No history")).toBeVisible();
  });
});
