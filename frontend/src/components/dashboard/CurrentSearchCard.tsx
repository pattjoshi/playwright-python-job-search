"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { STAGES } from "@/lib/constants";
import { formatClock, scoreBand } from "@/lib/format";
import type { Job } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useSearchSession } from "@/providers/SearchSessionProvider";

const BAND_STYLES = { good: "bg-success-soft text-success", ok: "bg-warning-soft text-warning", low: "bg-muted text-muted-foreground" };

/** The running search (live), or the best matches from the last one. */
export function CurrentSearchCard() {
  const { search, resumeApi } = useSearchSession();
  const { job, view } = search;
  const stageIndex = job ? STAGES.findIndex((stage) => stage.id === job.stage) : 0;
  const best: Job[] = (job?.result?.sites.flatMap((site) => site.jobs) ?? [])
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
    .slice(0, 3);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{view === "running" ? "Search running" : "Latest matches"}</CardTitle>
        <CardDescription>
          {view === "running" ? `${STAGES[stageIndex]?.text ?? "Starting…"} · ${formatClock(search.elapsed)}`
            : best.length ? "Best jobs from your last search" : "Run a search to see your best matches here"}
        </CardDescription>
        <CardAction>
          <Button asChild size="sm" variant={view === "running" ? "outline" : "default"}>
            <Link href="/search">{view === "running" ? "View progress" : best.length ? "All results" : "Start a search"}</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {view === "running" ? <Progress value={((stageIndex + 0.5) / STAGES.length) * 100} aria-label="Search progress" /> : null}
        {view !== "running" && best.length ? (
          <ul className="grid grid-cols-1 gap-2">
            {best.map((item) => (
              <li key={`${item.source}:${item.job_id}`} className="flex items-center gap-3 rounded-lg border p-3">
                <span className={cn("grid size-10 shrink-0 place-items-center rounded-full text-sm font-bold", BAND_STYLES[scoreBand(item.score)])}>
                  {item.score ?? "–"}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-medium">{item.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{[item.company, item.location].filter(Boolean).join(" · ")}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
        {view !== "running" && !best.length ? (
          <p className="text-sm text-muted-foreground">
            {resumeApi.resume ? `Resume ready: ${resumeApi.resume.file_name}` : "Start by uploading your resume on the Search page."}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
