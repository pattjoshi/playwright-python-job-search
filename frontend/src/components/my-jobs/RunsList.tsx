"use client";

import { useEffect, useState } from "react";

import { Badge, type BadgeKind } from "@/components/ui/Badge";
import { LinkButton } from "@/components/ui/Button";
import { api } from "@/lib/api/endpoints";
import { formatCost, formatDateTime, formatDuration, formatTokens } from "@/lib/format";
import type { Run, SiteConfig } from "@/lib/types";

import styles from "./ListItem.module.css";

const ORIGINS: Record<string, string> = { daily: "Daily", web: "Manual" };
const STATUS_BADGES: Record<string, BadgeKind> = { done: "done", stopped: "stopped", error: "error" };

function details(run: Run, sites: SiteConfig[]): string {
  const runSites = run.sites ?? {};
  const names = Object.fromEntries(sites.map((site) => [site.id, site.name]));
  const order = [...new Set([...sites.map((site) => site.id), ...Object.keys(runSites)])].filter((id) => runSites[id]);
  const siteText = order
    .map((id) => `${names[id] ?? id} ${runSites[id].status === "failed" ? "✕" : runSites[id].found}`)
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
  const [body, setBody] = useState<{ runs: Run[]; costs_configured: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.runs()
      .then((data) => !cancelled && setBody(data))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <li className={styles.empty}>{error}</li>;
  if (!body) return <li className={styles.empty}>Loading…</li>;
  return (
    <>
      {!body.costs_configured ? (
        <li className={styles.note}>
          Tip: set OPENAI_PRICE_INPUT and OPENAI_PRICE_OUTPUT in .env to see an estimated cost per run.
        </li>
      ) : null}
      {!body.runs.length ? (
        <li className={styles.empty}>No searches yet. Every search (from here or the daily search) shows up here.</li>
      ) : null}
      {body.runs.map((run) => {
        const funnel = (run.funnel ?? []).map(([label, count]) => `${count} ${label}`).join(" → ");
        return (
          <li key={run.id} className={styles.item}>
            <div className={styles.meta}>
              <div className={styles.runHead}>
                <b>{formatDateTime(run.started_at)}</b>
                <Badge kind={STATUS_BADGES[run.status] ?? "stopped"}>{run.status}</Badge>
                <Badge kind="site">{ORIGINS[run.origin] ?? "Command line"}</Badge>
              </div>
              <div className={styles.sub}>{details(run, sites)}</div>
              {funnel ? <div className={styles.sub}>{funnel}</div> : null}
              {run.error ? <div className={styles.runError}>{run.error}</div> : null}
            </div>
            {run.report_url ? <LinkButton href={run.report_url} external>Report</LinkButton> : null}
          </li>
        );
      })}
    </>
  );
}
