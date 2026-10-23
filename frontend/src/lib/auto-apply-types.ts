// Auto-apply shapes from /api/auto-apply (re-exported by types.ts).

export type AutoApplyStatus =
  | "queued" | "running" | "filled" | "submitted" | "unconfirmed" | "needs_answer" | "blocked" | "failed";

export interface AutoApplySettings {
  dry_run: boolean;
  min_score: number;
  daily_limit: number;
  show_browser: boolean;
  run_after_search: boolean;
  naukri: boolean;
  linkedin: boolean;
  indeed: boolean;
  board_daily_limit: number;
}

export type BoardId = "naukri" | "linkedin" | "indeed";

export interface AutoApplyJob {
  id: number;
  source: string;
  source_job_id: string;
  title: string;
  company: string;
  location: string;
  job_url: string;
  apply_url: string;
  platform: string;
  score: number | null;
  status: AutoApplyStatus;
  message: string;
  cover_letter: string;
  answers: { question: string; answer: string; how: string }[];
  screenshot: string;
  attempts: number;
  finished_at: string | null;
  has_page: boolean; // the page was saved when this job didn't go through (for fixing)
  created_at: string;
  updated_at: string;
}

export interface AutoApplyRun {
  status: "idle" | "running" | "stopping" | "signing_in" | "done" | "stopped" | "error";
  started_at: string | null;
  finished_at: string | null;
  logs: string[];
  applied: number;
  error: string | null;
}

export interface AutoApplyOverview {
  settings: AutoApplySettings;
  jobs: AutoApplyJob[];
  today: number;
  remaining: number;
  boards: Record<BoardId, { today: number; has_login: boolean; signed_in: boolean }>;
  run: AutoApplyRun;
}
