import { describe, expect, it } from "vitest";
import type { TrendQuery, TrendSnapshot } from "../../api/types";
import { TrendCache } from "./trendCache";

const query: TrendQuery = { start: "2026-08-10", end: "2026-08-17", bucket: "week" };
const snapshot = { ...query, training: [], health: [] } satisfies TrendSnapshot;

describe("TrendCache", () => {
  it("reuses a cached trend response for the same query", () => {
    const cache = new TrendCache();

    cache.set(query, snapshot);

    expect(cache.get({ ...query })).toBe(snapshot);
  });
});
