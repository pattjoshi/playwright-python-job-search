import { describe, expect, it } from "vitest";

import type { Application } from "@/lib/types";

import { isOverdue, matchesQuery, STATUS_BY_ID, STATUSES } from "./statuses";

const app = {
  company: "Acme Corp", title: "Frontend Developer", location: "Pune", contact: "Priya", notes: "Referred by Ravi",
} as Application;

describe("matchesQuery", () => {
  it("matches every word, in any field, ignoring case", () => {
    expect(matchesQuery(app, "acme pune")).toBe(true);
    expect(matchesQuery(app, "  RAVI ")).toBe(true);
    expect(matchesQuery(app, "")).toBe(true);
    expect(matchesQuery(app, "acme bangalore")).toBe(false);
  });
});

describe("isOverdue", () => {
  const today = new Date("2026-10-23T12:00:00Z");
  it("flags dates before today only", () => {
    expect(isOverdue("2026-10-22", today)).toBe(true);
    expect(isOverdue("2026-10-23", today)).toBe(false);
    expect(isOverdue(null, today)).toBe(false);
  });
});

describe("STATUSES", () => {
  it("covers every status the backend accepts, in pipeline order", () => {
    expect(STATUSES.map((s) => s.id)).toEqual(["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"]);
    expect(STATUS_BY_ID.offer.label).toBe("Offer");
  });
});
