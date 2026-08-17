import { describe, expect, it } from "vitest";
import { buildTrendQuery } from "./trendQuery";

describe("buildTrendQuery", () => {
  it.each([
    ["week", "2026-05-26"],
    ["month", "2025-08-23"],
    ["year", "2021-08-19"],
  ] as const)("requests real %s history ending at the exclusive dashboard end", (bucket, start) => {
    expect(buildTrendQuery("2026-08-18", bucket)).toEqual({
      start,
      end: "2026-08-18",
      bucket,
    });
  });
});
