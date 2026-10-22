/** Formatting helpers for numbers, times and job details shown on the page. */

import { DAY_LABELS } from "@/lib/constants";
import type { Job, RunStats } from "@/lib/types";

export function formatDuration(seconds: number | undefined | null): string {
  const s = Math.round(seconds || 0);
  return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
}

export function formatClock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function formatTokens(n: number | undefined): string {
  if (!n) return "0";
  return n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n);
}

export function formatCost(usd: number | null | undefined): string | null {
  if (usd == null) return null;
  return usd < 0.01 ? `~$${usd.toFixed(4)}` : `~$${usd.toFixed(2)}`;
}

/** "1m 36s · 15k AI tokens (~$0.0051) · 12 scores reused" */
export function statsParts(stats: RunStats | undefined): string[] {
  if (!stats) return [];
  const parts = [formatDuration(stats.duration_s)];
  if (stats.tokens) {
    const cost = formatCost(stats.cost_usd);
    parts.push(`${formatTokens(stats.tokens)} AI tokens${cost ? ` (${cost})` : ""}`);
  }
  if (stats.scores_reused) parts.push(`${stats.scores_reused} scores reused`);
  return parts;
}

export function formatTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function formatDays(days: string[]): string {
  if (days.length === 7) return "every day";
  if (days.join() === "mon,tue,wed,thu,fri") return "on weekdays";
  return "on " + days.map((day) => DAY_LABELS[day]).join(", ");
}

/** "today, 9:00 AM", "tomorrow, 9:00 AM" or "Mon, 6 Oct, 9:00 AM" */
export function formatWhen(iso: string, now = new Date()): string {
  const date = new Date(iso);
  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  const time = date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (date.toDateString() === now.toDateString()) return `today, ${time}`;
  if (date.toDateString() === tomorrow.toDateString()) return `tomorrow, ${time}`;
  return `${date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}, ${time}`;
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Only real web links are clickable (job data comes from other websites). */
export function safeUrl(url: string): string | null {
  return /^https?:\/\//.test(url) ? url : null;
}

export type ScoreBand = "good" | "ok" | "low";

export function scoreBand(score: number | null): ScoreBand {
  if (score == null) return "low";
  return score >= 75 ? "good" : score >= 50 ? "ok" : "low";
}

export function jobKey(job: Pick<Job, "source" | "job_id">): string {
  return `${job.source}:${job.job_id}`;
}

export function uniqueTrimmed(items: string[], limit: number): string[] {
  return [...new Set(items.map((item) => item.trim()).filter(Boolean))].slice(0, limit);
}
