"use client";

import { useCallback, useEffect, useState } from "react";

import { applicationsApi } from "@/lib/api/endpoints";
import type { Application, ApplicationInput } from "@/lib/types";

/** The tracker's applications: load, add, edit (moves update at once and roll back on error), delete. */
export function useApplications() {
  const [items, setItems] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setItems((await applicationsApi.list()).applications);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    applicationsApi.list()
      .then((body) => !cancelled && setItems(body.applications))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const create = useCallback(async (input: ApplicationInput) => {
    const { application } = await applicationsApi.create(input);
    setItems((current) => [application, ...(current ?? [])]);
    return application;
  }, []);

  const update = useCallback(async (id: number, input: ApplicationInput) => {
    let previous: Application[] | null = null;
    setItems((current) => {
      previous = current;
      return (current ?? []).map((item) => (item.id === id ? { ...item, ...input } : item));
    });
    try {
      const { application } = await applicationsApi.update(id, input);
      setItems((current) => (current ?? []).map((item) => (item.id === id ? application : item)));
      return application;
    } catch (err) {
      setItems(previous);
      throw err;
    }
  }, []);

  const remove = useCallback(async (id: number) => {
    await applicationsApi.remove(id);
    setItems((current) => (current ?? []).filter((item) => item.id !== id));
  }, []);

  return { items, error, reload, create, update, remove };
}

export type ApplicationsApi = ReturnType<typeof useApplications>;
