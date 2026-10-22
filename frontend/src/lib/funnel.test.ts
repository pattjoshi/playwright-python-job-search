import { describe, expect, it } from "vitest";

import { funnelHint } from "./funnel";
import type { FunnelStep } from "./types";

describe("funnelHint", () => {
  const steps: FunnelStep[] = [["found", 184], ["unique", 100], ["posted in 24h", 90], ["match 2-4 yrs", 20], ["checked", 20], ["scored", 6]];

  it("names the filter that removed the most jobs (never 'unique')", () => {
    expect(funnelHint(steps, { naukri: 12 })).toBe(
      "Only 6 jobs made it through. The “match 2-4 yrs” step removed 70. For more results, try a wider experience range (or Any).",
    );
  });

  it("stays quiet when enough jobs were found", () => {
    expect(funnelHint(steps, { naukri: 5 })).toBeNull();
    expect(funnelHint([["found", 1], ["scored", 1]], { naukri: 12 })).toBeNull();
  });
});
