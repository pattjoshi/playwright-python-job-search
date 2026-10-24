"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRuns } from "@/hooks/useRuns";
import { formatCost, formatDateTime, formatDuration, formatTokens } from "@/lib/format";
import type { Run, SiteConfig } from "@/lib/types";

import { EMPTY, NOTE, ROW, SUB } from "./list-styles";

const ORIGINS: Record<string, string> = { daily: "Daily", web: "Manual" };
const STATUS_STYLES: Record<string, string> = { done: "bg-success-soft text-success", error: "bg-destructive/10 text-destructive" };

function details(run: Run, sites: SiteConfig[]): string {
  const runSites = run.sites ?? {};
  const names = Object.fromEntries(sites.map((site) => [site.id, site.name]));
  const order = [...new Set([...sites.map((site) => site.id), ...Object.keys(runSites)])].filter((id) => runSites[id]);
  const siteText = order
    .map((id) => `${names[id] ?? id} ${["failed", "blocked"].includes(runSites[id].status) ? "✕" : runSites[id].found}`)
    .join(" · ");
  const tokens = (run.usage?.input_tokens ?? 0) + (run.usage?.output_tokens ?? 0);
  const cost = formatCost(run.cost_usd);
  return [
    formatDuration(run.duration_s),
    siteText,
    run.status === "done" ? `${run.shown} shown (${run.new} new)` : null,
    tokens ? `${formatTokens(tokens)} tokens${cost ? ` ${cost}` : ""}` : null,
    run.scores_reused ? `${run.scores_reused} reused` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Every search (from the page, the daily search or the command line), newest first. */
export function RunsList({ sites }: { sites: SiteConfig[] }) {
  const { runs, costsConfigured, error } = useRuns();

  if (error) return <li className={EMPTY}>{error}</li>;
  if (!runs) return <li className={EMPTY}>Loading…</li>;
  return (
    <>
      {!costsConfigured ? (
        <li className={NOTE}>
          Tip: set OPENAI_PRICE_INPUT and OPENAI_PRICE_OUTPUT in .env to see an estimated cost per run.
        </li>
      ) : null}
      {!runs.length ? (
        <li className={EMPTY}>No searches yet. Every search (from here or the daily search) shows up here.</li>
      ) : null}
      {runs.map((run) => {
        const funnel = (run.funnel ?? []).map(([label, count]) => `${count} ${label}`).join(" → ");
        return (
          <li key={run.id} className={ROW}>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <b>{formatDateTime(run.started_at)}</b>
                <Badge variant="secondary" className={STATUS_STYLES[run.status]}>{run.status}</Badge>
                <Badge variant="outline">{ORIGINS[run.origin] ?? "Command line"}</Badge>
              </div>
              <div className={SUB}>{details(run, sites)}</div>
              {funnel ? <div className={SUB}>{funnel}</div> : null}
              {run.error ? <div className="mt-1 text-xs text-destructive">{run.error}</div> : null}
            </div>
            {run.report_url ? (
              <Button asChild variant="outline" size="sm"><a href={run.report_url} target="_blank" rel="noopener noreferrer">Report</a></Button>
            ) : null}
          </li>
        );
      })}
    </>
  );
}
