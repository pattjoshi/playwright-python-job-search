/** Explains a short result list: which filter removed the most jobs, and what to change. */

import type { FunnelStep } from "@/lib/types";

const ADVICE: [match: string, advice: string][] = [
  ["posted in", "a longer time window"],
  ["yrs", "a wider experience range (or Any)"],
  ["new", "turning off “Only new jobs”"],
  ["checked", "a higher “Jobs to score per site” (Advanced)"],
  ["title fits", "more job titles in Keywords"],
];

export function funnelHint(steps: FunnelStep[], requested: Record<string, number>): string | null {
  if (steps.length < 3) return null;
  const wanted = Object.values(requested).reduce((a, b) => a + b, 0);
  const scored = steps[steps.length - 1][1];
  if (!wanted || scored >= wanted) return null;

  let worst: { drop: number; label: string } | null = null;
  for (let i = 1; i < steps.length; i++) {
    if (steps[i][0] === "unique") continue; // removing duplicates is never the problem
    const drop = steps[i - 1][1] - steps[i][1];
    if (!worst || drop > worst.drop) worst = { drop, label: steps[i][0] };
  }
  const advice = ADVICE.find(([match]) => worst?.label.includes(match))?.[1];
  if (!worst || worst.drop <= 0 || !advice) return null;
  return `Only ${scored} jobs made it through. The “${worst.label}” step removed ${worst.drop}. For more results, try ${advice}.`;
}
