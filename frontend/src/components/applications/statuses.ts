import type { Application, ApplicationStatus } from "@/lib/types";

export interface StatusInfo {
  id: ApplicationStatus;
  label: string;
  /** Tailwind classes for the badge / column accent (theme tokens only). */
  badge: string;
  dot: string;
}

/** The pipeline, in board order. */
export const STATUSES: StatusInfo[] = [
  { id: "saved", label: "Saved", badge: "bg-muted text-muted-foreground", dot: "bg-muted-foreground" },
  { id: "applied", label: "Applied", badge: "bg-accent text-accent-foreground", dot: "bg-primary" },
  { id: "screening", label: "Screening", badge: "bg-new-soft text-new", dot: "bg-new" },
  { id: "interview", label: "Interview", badge: "bg-warning-soft text-warning", dot: "bg-warning" },
  { id: "offer", label: "Offer", badge: "bg-success-soft text-success", dot: "bg-success" },
  { id: "rejected", label: "Rejected", badge: "bg-destructive/10 text-destructive", dot: "bg-destructive" },
  { id: "withdrawn", label: "Withdrawn", badge: "bg-muted text-muted-foreground", dot: "bg-muted-foreground/60" },
];

export const STATUS_BY_ID = Object.fromEntries(STATUSES.map((status) => [status.id, status])) as Record<ApplicationStatus, StatusInfo>;

export const SOURCE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn", naukri: "Naukri", indeed: "Indeed", manual: "Added by you", other: "Other",
};

/** "2026-10-23" → "23 Oct". */
export function shortDate(day: string | null): string {
  if (!day) return "";
  return new Date(`${day}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function isOverdue(day: string | null, today = new Date()): boolean {
  return !!day && day < today.toISOString().slice(0, 10);
}

/** True when every word of the search appears in the company, title, location, contact or notes. */
export function matchesQuery(app: Application, query: string): boolean {
  const text = [app.company, app.title, app.location, app.contact, app.notes].join(" ").toLowerCase();
  return query.toLowerCase().split(/\s+/).filter(Boolean).every((word) => text.includes(word));
}
