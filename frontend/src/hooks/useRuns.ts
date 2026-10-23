"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api/endpoints";
import type { Run } from "@/lib/types";

/** The search history from the backend; loads again whenever `reloadKey` changes. */
export function useRuns(reloadKey: unknown = null) {
  const [data, setData] = useState<{ runs: Run[]; costs_configured: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.runs()
      .then((body) => !cancelled && setData(body))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return { runs: data?.runs ?? null, costsConfigured: data?.costs_configured ?? true, error };
}
