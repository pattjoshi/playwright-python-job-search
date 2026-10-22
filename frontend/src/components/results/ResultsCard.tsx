"use client";

import { useState } from "react";

import { Download, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { jobKey, statsParts } from "@/lib/format";
import type { Job, JobStatus, SearchResult } from "@/lib/types";

import { HiddenJob, JobCard } from "./JobCard";

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
    <Card className="mt-4 gap-0 py-0">
      <div className="flex flex-wrap items-center gap-2.5 border-b px-5 py-3.5">
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold">{all.length} best matches</h2>
          <p className="text-sm text-muted-foreground">
            {[`${fresh} new`, `${result.scored} jobs scored`, ...statsParts(result.stats)].join(" · ")}
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <a href={result.html_report} target="_blank" rel="noopener noreferrer"><ExternalLink /> Open report</a>
        </Button>
        <Button asChild variant="outline" size="sm"><a href={result.excel_report}><Download /> Download Excel</a></Button>
      </div>
      <Tabs value={tab} onValueChange={setTab} className="gap-0">
        <div className="overflow-x-auto border-b px-5 py-2.5">
          <TabsList>
            {tabs.map((item) => (
              <TabsTrigger key={item.id} value={item.id}>
                {item.name}
                <span className="rounded-full bg-muted px-1.5 text-xs text-muted-foreground tabular-nums">{item.count}</span>
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
      </Tabs>
      <ul className="m-0 list-none p-0">
        {!jobs.length ? (
          <li className="px-5 py-7 text-center text-sm text-muted-foreground">
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
