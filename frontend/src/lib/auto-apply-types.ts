// Auto-apply shapes from /api/auto-apply (re-exported by types.ts).

export type AutoApplyStatus =
  | "queued" | "running" | "filled" | "submitted" | "unconfirmed" | "needs_answer" | "blocked" | "failed";

export interface AutoApplySettings {
  dry_run: boolean;
  min_score: number;
  daily_limit: number;
  show_browser: boolean;
  run_after_search: boolean;
}

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
  created_at: string;
  updated_at: string;
}

export interface AutoApplyRun {
  status: "idle" | "running" | "stopping" | "done" | "stopped" | "error";
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
  run: AutoApplyRun;
}
