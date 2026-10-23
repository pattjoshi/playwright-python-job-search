"use client";

import { useCallback, useEffect, useState } from "react";

import { autoApplyApi } from "@/lib/api/endpoints";
import type { AutoApplyOverview } from "@/lib/types";

const POLL_MS = 2000;

/** Auto-apply's settings, queue and run; polls while a run is going so the page follows it live. */
export function useAutoApply() {
  const [data, setData] = useState<AutoApplyOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setData(await autoApplyApi.overview());
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    autoApplyApi.overview()
      .then((body) => !cancelled && setData(body))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const active = data?.run.status === "running" || data?.run.status === "stopping";
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => void reload(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [active, reload]);

  return { data, error, reload, active };
}

export type AutoApplyApi = ReturnType<typeof useAutoApply>;
