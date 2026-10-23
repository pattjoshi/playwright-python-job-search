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

  const fail = useCallback((message: string) => {
    setError(message);
    return false;
  }, []);

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

  /** Save the schedule; returns true when it was saved. */
  const save = useCallback(
    async (search: SearchRequest): Promise<boolean> => {
      setError(null);
      if (!time) return fail("Pick a time.");
      if (!days.length) return fail("Pick at least one day.");
      setSaving(true);
      try {
        show(await api.saveDaily({ ...search, time, days, open_report: openReport }));
        return true;
      } catch (err) {
        return fail((err as Error).message);
      } finally {
        setSaving(false);
      }
    },
    [days, fail, openReport, show, time],
  );

  /** Remove the schedule; returns true when it was removed. */
  const turnOff = useCallback(async (): Promise<boolean> => {
    setError(null);
    try {
      show(await api.turnOffDaily());
      return true;
    } catch (err) {
      return fail((err as Error).message);
    }
  }, [fail, show]);

  return { status, time, setTime, days, setDays, openReport, setOpenReport, error, setError, saving, save, turnOff };
}

export type DailySearchApi = ReturnType<typeof useDailySearch>;
