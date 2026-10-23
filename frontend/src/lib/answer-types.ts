// Answer Bank shapes from /api/answers (re-exported by types.ts).

export type AnswerStatus = "answered" | "needs_review" | "needs_answer";
export type AnswerKind = "text" | "number" | "yes_no" | "choice";
export type AnswerCategory = "personal" | "experience" | "compensation" | "availability" | "work_authorization" | "other";

/** One question in the Answer Bank. `wordings` are other ways forms asked it. */
export interface Answer {
  id: number;
  question: string;
  answer: string;
  category: AnswerCategory;
  kind: AnswerKind;
  options: string[];
  status: AnswerStatus;
  source: "starter" | "resume" | "ai_draft" | "form" | "you" | string;
  asked_by: string;
  use_count: number;
  wordings: string[];
  created_at: string;
  updated_at: string;
}

export type AnswerInput = Partial<Pick<Answer, "question" | "answer" | "category" | "kind" | "options" | "wordings">>;

/** How a form question was answered: a saved wording, an AI match, an AI draft, or added for you to answer. */
export interface TryResult {
  how: "saved" | "matched" | "drafted" | "new";
  answer: string | null;
  entry: Answer;
}
