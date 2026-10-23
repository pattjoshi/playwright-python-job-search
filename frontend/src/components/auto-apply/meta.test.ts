import { describe, expect, it } from "vitest";

import type { AutoApplyJob } from "@/lib/types";

import { firstTab, inTab } from "./meta";

const job = (status: AutoApplyJob["status"]) => ({ status }) as AutoApplyJob;

describe("auto-apply tabs", () => {
  it("sorts jobs into Waiting, Needs you and Done", () => {
    expect(inTab(job("running"), "waiting")).toBe(true);
    expect(inTab(job("needs_answer"), "needs")).toBe(true);
    expect(inTab(job("filled"), "done")).toBe(true);
    expect(inTab(job("submitted"), "needs")).toBe(false);
  });

  it("opens on what needs you first", () => {
    expect(firstTab([job("submitted"), job("queued"), job("failed")])).toBe("needs");
    expect(firstTab([job("submitted"), job("queued")])).toBe("waiting");
    expect(firstTab([])).toBe("done");
  });
});
