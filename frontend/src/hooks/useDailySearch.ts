"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api/endpoints";
import { ALL_DAYS } from "@/lib/constants";
import type { DailyStatus, SearchRequest } from "@/lib/types";

/** The saved daily search: its form (time, days) and its status from the backend. */
export function useDailySearch() {
  const [status, setStatus] = useState<DailyStatus | null>(null);
  const [time, setTime] = useState("09:00");
  const [days, setDaysState] = useState<string[]>(ALL_DAYS);
  const [openReport, setOpenReport] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const setDays = useCallback((next: string[]) => setDaysState(ALL_DAYS.filter((day) => next.includes(day))), []);

  const show = useCallback(
    (next: DailyStatus) => {
      setStatus(next);
      if (next.schedule) {
        setTime(next.schedule.time);
        setDays(next.schedule.days);
        setOpenReport(next.schedule.open_report);
      }
    },
    [setDays],
  );

  useEffect(() => {
    api.daily().then(show).catch(() => {
      // the daily search is optional; the card just stays hidden
    });
  }, [show]);

  const save = useCallback(
    async (search: SearchRequest) => {
      setError(null);
      if (!time) return setError("Pick a time.");
      if (!days.length) return setError("Pick at least one day.");
      setSaving(true);
      try {
        show(await api.saveDaily({ ...search, time, days, open_report: openReport }));
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setSaving(false);
      }
    },
    [days, openReport, show, time],
  );

  const turnOff = useCallback(async () => {
    setError(null);
    try {
      show(await api.turnOffDaily());
    } catch (err) {
      setError((err as Error).message);
    }
  }, [show]);

  return { status, time, setTime, days, setDays, openReport, setOpenReport, error, setError, saving, save, turnOff };
}

export type DailySearchApi = ReturnType<typeof useDailySearch>;
