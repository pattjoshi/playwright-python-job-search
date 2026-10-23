"use client";

import { useEffect, useState } from "react";

import { applicationsApi } from "@/lib/api/endpoints";
import type { ApplicationStats } from "@/lib/types";

/** Tracker numbers for the dashboard: counts per status, applications per day, upcoming follow-ups. */
export function useApplicationStats() {
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    applicationsApi.stats().then(
      (body) => live && setStats(body),
      (err: Error) => live && setError(err.message),
    );
    return () => {
      live = false;
    };
  }, []);

  return { stats, error };
}
