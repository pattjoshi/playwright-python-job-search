"use client";

import { useCallback, useEffect, useState } from "react";

import { autoApplyApi } from "@/lib/api/endpoints";
import { waitForNextPoll } from "@/lib/poll";
import type { AutoApplyOverview } from "@/lib/types";

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

  const active = ["running", "stopping", "signing_in"].includes(data?.run.status ?? "");
  useEffect(() => {
    if (!active) return;
    let stopped = false;
    void (async () => {
      while (!stopped) {
        await waitForNextPoll();
        if (!stopped) await reload();
      }
    })();
    return () => {
      stopped = true;
    };
  }, [active, reload]);

  return { data, error, reload, active };
}

export type AutoApplyApi = ReturnType<typeof useAutoApply>;
