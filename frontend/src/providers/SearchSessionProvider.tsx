"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useDailySearch } from "@/hooks/useDailySearch";
import { useJobHistory } from "@/hooks/useJobHistory";
import { useResume } from "@/hooks/useResume";
import { buildRequest, useSearchForm } from "@/hooks/useSearchForm";
import { useSearchJob } from "@/hooks/useSearchJob";
import { useSessionRestore } from "@/hooks/useSessionRestore";
import { api } from "@/lib/api/endpoints";
import { clearSavedKeywords } from "@/lib/storage";
import type { Job, JobStatus, SearchJob } from "@/lib/types";
import { useConfig } from "@/providers/ConfigProvider";

function useSearchSessionValue() {
  const { config } = useConfig();
  const router = useRouter();
  const pathname = usePathname();
  const onSearchPage = useRef(pathname === "/search");
  const formApi = useSearchForm(config);
  const history = useJobHistory(config.history);
  const daily = useDailySearch();
  const resumeApi = useResume(formApi.fillFromResume);
  const [formError, setFormError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    onSearchPage.current = pathname === "/search";
  }, [pathname]);

  const { refresh, loadStatuses } = history;
  const onFinished = useCallback(
    (job: SearchJob) => {
      void refresh();
      if (job.status === "done") loadStatuses(job.result);
      if (onSearchPage.current) return;
      const view = { label: "View", onClick: () => router.push("/search") };
      const total = job.result?.sites.reduce((n, site) => n + site.jobs.length, 0) ?? 0;
      if (job.status === "done") toast.success(`Search complete · ${total} best matches`, { action: view });
      else if (job.status === "error") toast.error("The search stopped with an error", { action: view });
    },
    [loadStatuses, refresh, router],
  );
  const search = useSearchJob(onFinished);
  const { resume } = resumeApi;

  useSessionRestore(config, {
    restoreResume: (saved, keywords) => {
      resumeApi.restore(saved);
      formApi.setKeywords(keywords);
    },
    showSavedJob: (job) => {
      search.showSaved(job);
      if (job.status === "done") loadStatuses(job.result);
    },
    watch: search.watch,
  });

  /** Start a search with the current form; returns true when it started. */
  const startSearch = async (): Promise<boolean> => {
    setFormError(null);
    try {
      const request = buildRequest(formApi.form, resume?.resume_id);
      formApi.rememberSettings();
      setStarting(true);
      await search.start(request);
      return true;
    } catch (err) {
      setFormError((err as Error).message);
      return false;
    } finally {
      setStarting(false);
    }
  };

  const saveDaily = async () => {
    daily.setError(null);
    try {
      const request = buildRequest(formApi.form, resume?.resume_id);
      formApi.rememberSettings();
      if (await daily.save(request)) toast.success("Daily search saved");
    } catch (err) {
      daily.setError((err as Error).message);
    }
  };

  /** Remove the resume, keywords and results from the page (settings and history stay). */
  const clearPage = async () => {
    try {
      await api.clearSession();
    } catch (err) {
      setFormError((err as Error).message);
      return;
    }
    resumeApi.clear();
    search.reset();
    loadStatuses(null);
    formApi.update({ keywords: [] });
    clearSavedKeywords();
    setFormError(null);
    toast("Page cleared");
  };

  const setJobStatus = async (job: Job, status: JobStatus) => {
    try {
      const { tracked } = await history.setStatus(job, status);
      if (status === "applied") {
        toast.success(`Marked “${job.title}” as applied`, {
          description: tracked ? "Added to Applications" : undefined,
          action: { label: "Undo", onClick: () => void history.setStatus(job, "seen") },
        });
      }
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  const forgetSeen = async () => {
    try {
      await history.forgetSeen();
      toast("Seen jobs forgotten: they can show up as new again");
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  return {
    formApi, history, daily, resumeApi, search, formError, starting,
    canStart: !!resume && config.has_api_key && !starting,
    startSearch, saveDaily, clearPage, setJobStatus, forgetSeen,
  };
}

export type SearchSession = ReturnType<typeof useSearchSessionValue>;

const SearchSessionContext = createContext<SearchSession | null>(null);

/**
 * Holds the search page's state for the whole app, so moving to another page and back keeps the
 * resume, the form and a running search (which keeps being followed in the background).
 */
export function SearchSessionProvider({ children }: { children: React.ReactNode }) {
  const value = useSearchSessionValue();
  return <SearchSessionContext.Provider value={value}>{children}</SearchSessionContext.Provider>;
}

export function useSearchSession(): SearchSession {
  const value = useContext(SearchSessionContext);
  if (!value) throw new Error("useSearchSession must be used inside <SearchSessionProvider>");
  return value;
}
