import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("../features/dashboard/DashboardPage", () => ({
  DashboardPage: () => <main>Garmin Training Dashboard</main>,
}));

describe("App", () => {
  it("renders the dashboard application shell", () => {
    render(<App />);
    expect(screen.getByRole("main")).toHaveTextContent("Garmin Training Dashboard");
  });
});
