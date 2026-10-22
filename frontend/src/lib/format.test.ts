import { describe, expect, it } from "vitest";

import { formatCost, formatDays, formatDuration, formatTokens, safeUrl, scoreBand, statsParts, uniqueTrimmed } from "./format";

describe("format", () => {
  it("formats durations, tokens and cost", () => {
    expect(formatDuration(96)).toBe("1m 36s");
    expect(formatDuration(42.4)).toBe("42s");
    expect(formatTokens(14900)).toBe("15k");
    expect(formatTokens(1500)).toBe("1.5k");
    expect(formatTokens(800)).toBe("800");
    expect(formatCost(0.0051)).toBe("~$0.0051");
    expect(formatCost(1.234)).toBe("~$1.23");
    expect(formatCost(null)).toBeNull();
  });

  it("builds the results stats line", () => {
    const stats = { duration_s: 96, ai_calls: 4, tokens: 14900, cached_tokens: 0, cost_usd: 0.0051, scores_reused: 12, descriptions_reused: 0 };
    expect(statsParts(stats)).toEqual(["1m 36s", "15k AI tokens (~$0.0051)", "12 scores reused"]);
    expect(statsParts(undefined)).toEqual([]);
  });

  it("describes the daily schedule days", () => {
    expect(formatDays(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])).toBe("every day");
    expect(formatDays(["mon", "tue", "wed", "thu", "fri"])).toBe("on weekdays");
    expect(formatDays(["sat", "sun"])).toBe("on Sat, Sun");
  });

  it("only lets real web links through", () => {
    expect(safeUrl("https://www.naukri.com/job/1")).toBe("https://www.naukri.com/job/1");
    expect(safeUrl("javascript:alert(1)")).toBeNull();
  });

  it("bands scores and cleans lists", () => {
    expect([scoreBand(90), scoreBand(60), scoreBand(20), scoreBand(null)]).toEqual(["good", "ok", "low", "low"]);
    expect(uniqueTrimmed([" SDET ", "QA", "SDET", ""], 8)).toEqual(["SDET", "QA"]);
  });
});
