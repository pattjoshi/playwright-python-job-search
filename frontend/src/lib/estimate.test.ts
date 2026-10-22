import { describe, expect, it } from "vitest";

import { estimateSearch } from "./estimate";

const base = { keywords: 3, locations: ["Pune", "Remote"], maxPages: 3, top: 40, parallel: true };

describe("estimateSearch", () => {
  it("asks for a site when none is picked", () => {
    expect(estimateSearch({ ...base, sites: [] })).toEqual({ text: "Pick at least one job site", tip: false });
  });

  it("counts Naukri cities in one search and runs sites side by side", () => {
    const result = estimateSearch({ ...base, sites: ["linkedin", "naukri"] });
    expect(result.text).toBe("12 searches across 2 sites · about 4 min (sites run at the same time)");
    expect(result.tip).toBe(false);
  });

  it("adds sites up when they run one after another, and suggests fewer searches", () => {
    const many = estimateSearch({ ...base, keywords: 8, locations: ["Pune", "Delhi"], sites: ["linkedin", "indeed"], parallel: false });
    expect(many.text).toMatch(/^32 searches across 2 sites · about \d+ min$/);
    expect(many.tip).toBe(true);
  });
});
