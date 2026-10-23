import type { AutoApplyJob, AutoApplyStatus } from "@/lib/types";

export const STATUS_BADGE: Record<AutoApplyStatus, { label: string; className: string }> = {
  queued: { label: "Waiting", className: "bg-muted text-muted-foreground" },
  running: { label: "Applying…", className: "bg-new-soft text-new" },
  filled: { label: "Filled (dry run)", className: "bg-accent text-accent-foreground" },
  submitted: { label: "Submitted", className: "bg-success-soft text-success" },
  unconfirmed: { label: "Submitted?", className: "bg-warning-soft text-warning" },
  needs_answer: { label: "Needs your answer", className: "bg-warning-soft text-warning" },
  blocked: { label: "Do it yourself", className: "bg-destructive/10 text-destructive" },
  failed: { label: "Failed", className: "bg-destructive/10 text-destructive" },
};

export const PLATFORM_NAMES: Record<string, string> = {
  greenhouse: "Greenhouse", lever: "Lever", ashby: "Ashby", smartrecruiters: "SmartRecruiters", workday: "Workday",
  other: "Company site",
};

export type QueueTab = "waiting" | "needs" | "done";

export const TABS: { id: QueueTab; label: string; statuses: AutoApplyStatus[]; empty: string }[] = [
  { id: "waiting", label: "Waiting", statuses: ["queued", "running"],
    empty: "Nothing waiting. Matches from your searches with a company application page are added here." },
  { id: "needs", label: "Needs you", statuses: ["needs_answer", "blocked", "failed"], empty: "Nothing needs you right now." },
  { id: "done", label: "Done", statuses: ["submitted", "unconfirmed", "filled"], empty: "No applications yet." },
];

export function inTab(job: AutoApplyJob, tab: QueueTab): boolean {
  return TABS.find((t) => t.id === tab)!.statuses.includes(job.status);
}

/** The tab to open on: what needs you, else what's waiting, else what's done. */
export function firstTab(jobs: AutoApplyJob[]): QueueTab {
  if (jobs.some((job) => inTab(job, "needs"))) return "needs";
  if (jobs.some((job) => inTab(job, "waiting"))) return "waiting";
  return "done";
}
