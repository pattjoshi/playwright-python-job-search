"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/endpoints";
import { safeUrl } from "@/lib/format";
import type { HistoryCounts, JobStatus, SavedJob } from "@/lib/types";

import { EMPTY, ROW, SUB } from "./list-styles";

interface SavedJobsListProps {
  status: "applied" | "hidden";
  names: Record<string, string>;
  onCounts: (counts: HistoryCounts) => void;
  onUndo: (job: SavedJob, status: JobStatus) => Promise<void>;
}

const EMPTY_TEXT = {
  applied: "No applied jobs yet. Click “Mark applied” on a job to track it here.",
  hidden: "No hidden jobs.",
};

export function SavedJobsList({ status, names, onCounts, onUndo }: SavedJobsListProps) {
  const [jobs, setJobs] = useState<SavedJob[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api.savedJobs(status)
      .then((body) => {
        if (cancelled) return;
        setJobs(body.jobs);
        onCounts(body.history);
      })
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [status, version, onCounts]);

  if (error) return <li className={EMPTY}>{error}</li>;
  if (!jobs) return <li className={EMPTY}>Loading…</li>;
  if (!jobs.length) return <li className={EMPTY}>{EMPTY_TEXT[status]}</li>;
  return (
    <>
      {jobs.map((job) => {
        const url = safeUrl(job.url);
        const when = new Date(job.updated_at).toLocaleDateString(undefined, { day: "numeric", month: "short" });
        const title = job.title || "Untitled job";
        return (
          <li key={`${job.source}:${job.job_id}`} className={ROW}>
            <div className="min-w-0 flex-1">
              {url ? <a href={url} target="_blank" rel="noopener noreferrer">{title}</a> : <b>{title}</b>}
              <div className={SUB}>{[job.company, names[job.source] ?? job.source, `${status} ${when}`].filter(Boolean).join(" · ")}</div>
            </div>
            <Button variant="outline" size="sm" onClick={() => onUndo(job, "seen").then(() => setVersion((v) => v + 1))}>Undo</Button>
          </li>
        );
      })}
    </>
  );
}
