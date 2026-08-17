import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Gauge } from "./Gauge";

describe("Gauge", () => {
  it("renders value and label as text alongside its SVG visual", () => {
    render(<Gauge value={72} min={0} max={100} label="Recovery" color="green" />);

    expect(screen.getByText("72")).toBeVisible();
    expect(screen.getByText("Recovery")).toBeVisible();
    expect(screen.getByRole("img", { name: /recovery: 72/i })).toBeInTheDocument();
  });
});
