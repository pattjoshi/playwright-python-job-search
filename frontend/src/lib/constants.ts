import type { Stage } from "@/lib/types";

export const POLL_MS = 1200;
export const MAX_KEYWORDS = 8;
export const MAX_LOCATIONS = 10;
export const REMOTE = "Remote";

export const STAGES: { id: Stage; label: string; text: string }[] = [
  { id: "resume", label: "Resume", text: "Preparing…" },
  { id: "search", label: "Search", text: "Searching job sites…" },
  { id: "details", label: "Details", text: "Reading job details…" },
  { id: "score", label: "Scoring", text: "Scoring jobs against your resume…" },
  { id: "report", label: "Done", text: "Building your report…" },
];

export const HOUR_OPTIONS = [
  { hours: 12, label: "12 hours" },
  { hours: 24, label: "24 hours" },
  { hours: 72, label: "3 days" },
  { hours: 168, label: "7 days" },
];

export const DAY_LABELS: Record<string, string> = {
  mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun",
};
export const ALL_DAYS = Object.keys(DAY_LABELS);
export const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"];
