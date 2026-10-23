"use client";

import { useCallback, useState } from "react";

import { api } from "@/lib/api/endpoints";
import { jobKey } from "@/lib/format";
import type { HistoryCounts, Job, JobStatus, SearchResult } from "@/lib/types";

/** Applied / hidden / seen counts, and the status of each job shown in the results. */
export function useJobHistory(initial: HistoryCounts) {
  const [counts, setCounts] = useState<HistoryCounts>(initial);
  const [statuses, setStatuses] = useState<Record<string, JobStatus>>({});

  /** Start from the statuses the backend sent with the results (applied/hidden before a reload). */
  const loadStatuses = useCallback((result: SearchResult | null) => {
    const next: Record<string, JobStatus> = {};
    for (const site of result?.sites ?? []) {
      for (const job of site.jobs) if (job.status && job.status !== "seen") next[jobKey(job)] = job.status;
    }
    setStatuses(next);
  }, []);

  const setStatus = useCallback(async (job: Pick<Job, "source" | "job_id"> & Partial<Job>, status: JobStatus) => {
    const body = await api.setJobStatus(
      { source: job.source, job_id: job.job_id, title: job.title, company: job.company, url: job.url, location: job.location },
      status,
    );
    setStatuses((current) => {
      const next = { ...current };
      if (status === "seen") delete next[jobKey(job)];
      else next[jobKey(job)] = status;
      return next;
    });
    setCounts(body.history);
    return body;
  }, []);

  const refresh = useCallback(async () => {
    try {
      setCounts((await api.config()).history);
    } catch {
      // keep the old counts
    }
  }, []);

  const forgetSeen = useCallback(async () => setCounts((await api.forgetSeen()).history), []);

  return { counts, setCounts, statuses, loadStatuses, setStatus, refresh, forgetSeen };
}

export type JobHistoryApi = ReturnType<typeof useJobHistory>;
