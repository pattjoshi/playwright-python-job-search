import type { Answer, AnswerCategory, AnswerKind, AnswerStatus } from "@/lib/types";

export const CATEGORIES: { id: AnswerCategory; label: string }[] = [
  { id: "personal", label: "Personal details" },
  { id: "experience", label: "Experience and education" },
  { id: "compensation", label: "Salary" },
  { id: "availability", label: "Availability" },
  { id: "work_authorization", label: "Work authorization" },
  { id: "other", label: "Other" },
];
export const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.id, c.label])) as Record<AnswerCategory, string>;

export const KINDS: { id: AnswerKind; label: string }[] = [
  { id: "text", label: "Text" },
  { id: "number", label: "Number" },
  { id: "yes_no", label: "Yes / No" },
  { id: "choice", label: "Pick one option" },
];

/** The tabs, in the order they matter: what needs you first. */
export const STATUS_TABS: { id: AnswerStatus | "all"; label: string }[] = [
  { id: "needs_answer", label: "Needs answer" },
  { id: "needs_review", label: "Needs review" },
  { id: "answered", label: "Answered" },
  { id: "all", label: "All" },
];

export const STATUS_BADGE: Record<AnswerStatus, { label: string; className: string }> = {
  needs_answer: { label: "Needs answer", className: "bg-destructive/10 text-destructive" },
  needs_review: { label: "AI draft · review", className: "bg-warning-soft text-warning" },
  answered: { label: "Answered", className: "bg-success-soft text-success" },
};

export const SOURCE_LABEL: Record<string, string> = {
  starter: "Common question", resume: "Filled from your resume", ai_draft: "Drafted by AI from a form",
  form: "Asked by a form", you: "Added by you",
};

export type StatusCounts = Record<AnswerStatus, number>;

export function countByStatus(items: Answer[]): StatusCounts {
  const counts: StatusCounts = { needs_answer: 0, needs_review: 0, answered: 0 };
  for (const item of items) counts[item.status] += 1;
  return counts;
}

/** The tab to open on: whatever needs you, else everything. */
export function firstTab(counts: StatusCounts): AnswerStatus | "all" {
  if (counts.needs_answer) return "needs_answer";
  if (counts.needs_review) return "needs_review";
  return "all";
}

/** True when every word of the search is in the question, its other wordings or the answer. */
export function matchesSearch(item: Answer, query: string): boolean {
  const text = [item.question, item.answer, ...item.wordings].join(" ").toLowerCase();
  return query.toLowerCase().split(/\s+/).filter(Boolean).every((word) => text.includes(word));
}
