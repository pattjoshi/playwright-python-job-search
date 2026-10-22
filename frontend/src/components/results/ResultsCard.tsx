"use client";

import { useState } from "react";

import { LinkButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { jobKey, statsParts } from "@/lib/format";
import type { Job, JobStatus, SearchResult } from "@/lib/types";

import { HiddenJob, JobCard } from "./JobCard";
import styles from "./ResultsCard.module.css";

interface ResultsCardProps {
  result: SearchResult;
  statuses: Record<string, JobStatus>;
  onSetStatus: (job: Job, status: JobStatus) => void;
}

const byScore = (a: Job, b: Job) => (b.score ?? -1) - (a.score ?? -1);

/** The best matches: one tab for all sites (best first) and one per site. */
export function ResultsCard({ result, statuses, onSetStatus }: ResultsCardProps) {
  const [tab, setTab] = useState("all");
  const all = result.sites.flatMap((site) => site.jobs);
  const fresh = all.filter((job) => job.is_new).length;
  const names = Object.fromEntries(result.sites.map((site) => [site.id, site.name]));
  const jobs = tab === "all" ? [...all].sort(byScore) : result.sites.find((site) => site.id === tab)?.jobs ?? [];
  const tabs = [
    { id: "all", name: "All", count: all.length },
    ...result.sites.map((site) => ({ id: site.id, name: site.name, count: site.jobs.length })),
  ];

  return (
    <Card className={styles.results}>
      <div className={styles.head}>
        <div>
          <h2>{all.length} best matches</h2>
          <div className={styles.sub}>
            {[`${fresh} new`, `${result.scored} jobs scored`, ...statsParts(result.stats)].join(" · ")}
          </div>
        </div>
        <span className={styles.spacer} />
        <LinkButton href={result.html_report} external>Open report</LinkButton>
        <LinkButton href={result.excel_report}>Download Excel</LinkButton>
      </div>
      <Tabs tabs={tabs} selected={tab} onSelect={setTab} />
      <ul className={styles.list}>
        {!jobs.length ? (
          <li className={styles.empty}>
            No matching jobs here. Try more locations, other keywords, a wider experience range or a longer time window.
          </li>
        ) : null}
        {jobs.map((job, index) => {
          const status = statuses[jobKey(job)];
          return status === "hidden" ? (
            <HiddenJob key={jobKey(job)} job={job} onUndo={() => onSetStatus(job, "seen")} />
          ) : (
            <JobCard
              key={jobKey(job)} job={job} rank={index + 1} applied={status === "applied"}
              siteName={tab === "all" ? names[job.source] : undefined} onSetStatus={(next) => onSetStatus(job, next)}
            />
          );
        })}
      </ul>
    </Card>
  );
}
