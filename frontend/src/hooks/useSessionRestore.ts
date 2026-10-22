"use client";

import { useEffect, useRef } from "react";

import { api } from "@/lib/api/endpoints";
import { loadSavedKeywords } from "@/lib/storage";
import type { AppConfig, Resume, SearchJob } from "@/lib/types";

interface RestoreHandlers {
  restoreResume: (resume: Resume, keywords: string[]) => void;
  showSavedJob: (job: SearchJob) => void;
  watch: (jobId: string) => void;
}

/**
 * On page load: bring back the resume and last search from the saved session (so a reload or an
 * app restart doesn't wipe the page), and follow a search that is still running.
 */
export function useSessionRestore(config: AppConfig, handlers: RestoreHandlers) {
  const done = useRef(false);
  const latest = useRef(handlers);

  useEffect(() => {
    latest.current = handlers;
  });

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const { restoreResume, showSavedJob, watch } = latest.current;
    api.session()
      .then((saved) => {
        if (saved.resume) restoreResume(saved.resume, loadSavedKeywords() ?? saved.resume.profile.keywords);
        if (saved.last_job && !config.running_job) showSavedJob(saved.last_job);
      })
      .catch(() => {
        // nothing saved yet
      })
      .finally(() => {
        if (config.running_job) watch(config.running_job);
      });
  }, [config.running_job]);
}
