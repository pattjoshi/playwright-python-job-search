import type { Job } from "@/lib/types";

export type ResultSort = "score" | "newest" | "company";

export interface ResultFilter {
  minScore: number; // 0 = any
  maxHours: number | null; // posted within, null = any
  query: string; // words in the title, company or location
  sort: ResultSort;
}

export const NO_FILTER: ResultFilter = { minScore: 0, maxHours: null, query: "", sort: "score" };

const SUFFIXES = /\b(private|pvt|limited|ltd|llp|inc|incorporated|corp|corporation|co|company|technologies|india)\b/g;

/** "Acme Technologies Pvt. Ltd." and "ACME" are the same company (same rule as the backend). */
export function companyKey(name: string): string {
  const words = (name || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ");
  return words.replace(SUFFIXES, " ").replace(/\s+/g, " ").trim() || words.trim();
}

const SORTS: Record<ResultSort, (a: Job, b: Job) => number> = {
  score: (a, b) => (b.score ?? -1) - (a.score ?? -1),
  newest: (a, b) => (a.hours_ago ?? Infinity) - (b.hours_ago ?? Infinity),
  company: (a, b) => a.company.localeCompare(b.company),
};

/** The jobs to show, and how many the filters (and hidden companies) left out. */
export function filterJobs(jobs: Job[], filter: ResultFilter, hiddenCompanies: string[]): { shown: Job[]; left_out: number } {
  const hidden = new Set(hiddenCompanies.map(companyKey));
  const words = filter.query.toLowerCase().split(/\s+/).filter(Boolean);
  const shown = jobs.filter((job) => {
    if (hidden.has(companyKey(job.company))) return false;
    if (filter.minScore && (job.score ?? 0) < filter.minScore) return false;
    if (filter.maxHours !== null && job.hours_ago != null && job.hours_ago > filter.maxHours) return false;
    const text = `${job.title} ${job.company} ${job.location}`.toLowerCase();
    return words.every((word) => text.includes(word));
  });
  return { shown: [...shown].sort(SORTS[filter.sort]), left_out: jobs.length - shown.length };
}

export function isFiltered(filter: ResultFilter): boolean {
  return filter.minScore > 0 || filter.maxHours !== null || filter.query.trim() !== "";
}

/** "3 hours ago" for the details panel. */
export function postedAgo(hours: number | null | undefined): string {
  if (hours == null) return "";
  if (hours < 1) return "just now";
  if (hours < 48) return `${Math.round(hours)} hour${Math.round(hours) === 1 ? "" : "s"} ago`;
  return `${Math.round(hours / 24)} days ago`;
}
