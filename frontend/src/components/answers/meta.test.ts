import { describe, expect, it } from "vitest";

import type { Answer } from "@/lib/types";

import { countByStatus, firstTab, matchesSearch } from "./meta";

const answer = (status: Answer["status"], extra: Partial<Answer> = {}) =>
  ({ question: "Notice period", answer: "30 days", wordings: ["How soon can you join?"], status, ...extra }) as Answer;

describe("Answer Bank helpers", () => {
  it("counts questions per status and opens on what needs you", () => {
    const counts = countByStatus([answer("answered"), answer("needs_review"), answer("needs_review")]);
    expect(counts).toEqual({ answered: 1, needs_review: 2, needs_answer: 0 });
    expect(firstTab(counts)).toBe("needs_review");
    expect(firstTab({ ...counts, needs_answer: 1 })).toBe("needs_answer");
    expect(firstTab({ answered: 3, needs_review: 0, needs_answer: 0 })).toBe("all");
  });

  it("searches the question, its other wordings and the answer", () => {
    expect(matchesSearch(answer("answered"), "join soon")).toBe(true);
    expect(matchesSearch(answer("answered"), "30 DAYS")).toBe(true);
    expect(matchesSearch(answer("answered"), "salary")).toBe(false);
  });
});
