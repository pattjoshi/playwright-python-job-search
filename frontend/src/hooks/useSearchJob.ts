"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api/endpoints";
import { POLL_MS } from "@/lib/constants";
import type { SearchJob, SearchRequest } from "@/lib/types";

export type RunView = "idle" | "running" | "finished";

const isActive = (job: SearchJob) => job.status === "running" || job.status === "stopping";

/** Stands in for a search whose status couldn't be read (e.g. the app was closed). */
function failedJob(id: string, last: SearchJob | null): SearchJob {
  return {
    id, stage: "resume", started_at: "", finished_at: null, logs: [], sites: {}, progress: null, funnel: null,
    requested: {}, profile: null, result: null, ...last, status: "error", error: null,
  };
}

/**
 * Starts a search, polls its status until it ends, and keeps the last finished search on screen.
 * `restored` is true when the shown search came from the saved session (a reload), not this visit.
 */
export function useSearchJob(onFinished: (job: SearchJob) => void) {
  const [job, setJob] = useState<SearchJob | null>(null);
  const [view, setView] = useState<RunView>("idle");
  const [restored, setRestored] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [stopping, setStopping] = useState(false);
  const watching = useRef<string | null>(null);
  const latest = useRef<SearchJob | null>(null);
  const finishedRef = useRef(onFinished);

  useEffect(() => {
    finishedRef.current = onFinished;
  }, [onFinished]);

  useEffect(() => {
    if (view !== "running") return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [view]);

  const show = useCallback((next: SearchJob | null) => {
    latest.current = next;
    setJob(next);
  }, []);

  const finish = useCallback((ended: SearchJob) => {
    watching.current = null;
    show(ended);
    setView("finished");
    setStopping(false);
    finishedRef.current(ended);
  }, [show]);

  /** Ask for the status every POLL_MS until the search ends (or another search is being watched). */
  const poll = useCallback(
    async (id: string) => {
      while (watching.current === id) {
        try {
          const current = await api.searchStatus(id);
          if (watching.current !== id) return;
          show(current);
          if (!isActive(current)) return finish(current);
        } catch (err) {
          if (watching.current !== id) return;
          setError(`${(err as Error).message}. Is the app still running?`);
          return finish(failedJob(id, latest.current));
        }
        await new Promise((resolve) => window.setTimeout(resolve, POLL_MS));
      }
    },
    [finish, show],
  );

  const watch = useCallback(
    (id: string) => {
      watching.current = id;
      show(null);
      setRestored(false);
      setError(null);
      setElapsed(0);
      setStopping(false);
      setView("running");
      void poll(id);
    },
    [poll, show],
  );

  const start = useCallback(
    async (search: SearchRequest) => {
      const { id } = await api.startSearch(search);
      watch(id);
    },
    [watch],
  );

  const stop = useCallback(async () => {
    const id = watching.current;
    if (!id) return;
    setStopping(true);
    try {
      await api.stopSearch(id);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  /** Show a search that finished before the page was reloaded, without polling. */
  const showSaved = useCallback((saved: SearchJob) => {
    show(saved);
    setRestored(true);
    setError(null);
    setView("finished");
  }, [show]);

  const reset = useCallback(() => {
    watching.current = null;
    show(null);
    setView("idle");
    setRestored(false);
    setError(null);
  }, [show]);

  return { job, view, restored, error, setError, elapsed, stopping, start, stop, watch, showSaved, reset };
}

export type SearchJobApi = ReturnType<typeof useSearchJob>;
