import { describe, expect, it } from "vitest";
import { formatDistance, formatDuration, formatInclusivePeriod } from "./formatters";

describe("formatDuration", () => {
  it("renders unavailable values explicitly", () => {
    expect(formatDuration(null)).toBe("Unavailable");
  });

  it("handles minute and hour boundaries", () => {
    expect(formatDuration(59)).toBe("0m");
    expect(formatDuration(60)).toBe("1m");
    expect(formatDuration(3599)).toBe("59m");
    expect(formatDuration(3600)).toBe("1h 0m");
    expect(formatDuration(3661)).toBe("1h 1m");
  });
});

describe("formatDistance", () => {
  it("renders unavailable values explicitly", () => {
    expect(formatDistance(null)).toBe("Unavailable");
  });

  it("rounds meters to one decimal kilometer", () => {
    expect(formatDistance(0)).toBe("0.0 km");
    expect(formatDistance(1449)).toBe("1.4 km");
    expect(formatDistance(1450)).toBe("1.5 km");
    expect(formatDistance(1499)).toBe("1.5 km");
  });
});

describe("formatInclusivePeriod", () => {
  it("renders an exclusive API end as the inclusive human date", () => {
    expect(formatInclusivePeriod("2026-08-10", "2026-08-18")).toBe(
      "2026-08-10 – 2026-08-17",
    );
  });
});
