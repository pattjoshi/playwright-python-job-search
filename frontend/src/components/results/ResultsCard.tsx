"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Download, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSearchFilters } from "@/hooks/useSearchFilters";
import { jobKey, statsParts } from "@/lib/format";
import { filterJobs, NO_FILTER, type ResultFilter } from "@/lib/results-filter";
import type { Job, JobStatus, SearchResult } from "@/lib/types";

import { HiddenJob, JobCard } from "./JobCard";
import { JobDetailsSheet } from "./JobDetailsSheet";
import { ResultsFilters } from "./ResultsFilters";

interface ResultsCardProps {
  result: SearchResult;
  statuses: Record<string, JobStatus>;
  onSetStatus: (job: Job, status: JobStatus) => void;
}

/** The best matches: one tab for all sites and one per site, narrowed and sorted by the filters. */
export function ResultsCard({ result, statuses, onSetStatus }: ResultsCardProps) {
  const [tab, setTab] = useState("all");
  const [filter, setFilter] = useState<ResultFilter>(NO_FILTER);
  const [open, setOpen] = useState<Job | null>(null);
  const { hiddenCompanies, hideCompany, showCompany } = useSearchFilters();
  const all = result.sites.flatMap((site) => site.jobs);
  const fresh = all.filter((job) => job.is_new).length;
  const names = Object.fromEntries(result.sites.map((site) => [site.id, site.name]));
  const count = (jobs: Job[]) => filterJobs(jobs, filter, hiddenCompanies).shown.length;
  const { shown: jobs, left_out } = filterJobs(
    tab === "all" ? all : result.sites.find((site) => site.id === tab)?.jobs ?? [], filter, hiddenCompanies,
  );
  const tabs = [
    { id: "all", name: "All", count: count(all) },
    ...result.sites.map((site) => ({ id: site.id, name: site.name, count: count(site.jobs) })),
  ];

  const hide = async (job: Job) => {
    try {
      await hideCompany(job.company);
      setOpen(null);
      toast.success(`Hiding ${job.company} from results and future searches`, {
        action: { label: "Undo", onClick: () => void showCompany(job.company) },
      });
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

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
      <ResultsFilters
        filter={filter} onChange={setFilter} leftOut={left_out}
        hiddenCompanies={hiddenCompanies} onShowCompany={(company) => void showCompany(company)}
      />
      <ul className="m-0 list-none p-0">
        {!jobs.length ? (
          <li className="px-5 py-7 text-center text-sm text-muted-foreground">
            {left_out
              ? "Every job here is left out by the filters above."
              : "No matching jobs here. Try more locations, other keywords, a wider experience range or a longer time window."}
          </li>
        ) : null}
        {jobs.map((job, index) => {
          const status = statuses[jobKey(job)];
          return status === "hidden" ? (
            <HiddenJob key={jobKey(job)} job={job} onUndo={() => onSetStatus(job, "seen")} />
          ) : (
            <JobCard
              key={jobKey(job)} job={job} rank={index + 1} applied={status === "applied"}
              siteName={tab === "all" ? names[job.source] : undefined}
              onSetStatus={(next) => onSetStatus(job, next)} onDetails={() => setOpen(job)}
            />
          );
        })}
      </ul>
      <JobDetailsSheet
        job={open} siteName={open ? names[open.source] : undefined} applied={!!open && statuses[jobKey(open)] === "applied"}
        onClose={() => setOpen(null)} onSetStatus={onSetStatus} onHideCompany={hide}
      />
    </Card>
  );
}
