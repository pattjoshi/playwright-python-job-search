"use client";

import { useCallback, useRef, useState } from "react";

import { DailySearchCard } from "@/components/daily/DailySearchCard";
import { Header, type PillKind } from "@/components/layout/Header";
import { MyJobsSheet, type MyJobsTab } from "@/components/my-jobs/MyJobsSheet";
import { ProgressCard } from "@/components/progress/ProgressCard";
import { ResumeCard } from "@/components/resume/ResumeCard";
import { EmptyState } from "@/components/results/EmptyState";
import { ResultsCard } from "@/components/results/ResultsCard";
import { ActionsCard } from "@/components/search-form/ActionsCard";
import { LookForCard } from "@/components/search-form/LookForCard";
import { OptionsCard } from "@/components/search-form/OptionsCard";
import { SitesCard } from "@/components/search-form/SitesCard";
import { Alert } from "@/components/ui/Alert";
import { useDailySearch } from "@/hooks/useDailySearch";
import { useJobHistory } from "@/hooks/useJobHistory";
import { useResume } from "@/hooks/useResume";
import { buildRequest, chosenSites, useSearchForm } from "@/hooks/useSearchForm";
import { useSearchJob } from "@/hooks/useSearchJob";
import { useSessionRestore } from "@/hooks/useSessionRestore";
import { api } from "@/lib/api/endpoints";
import { estimateSearch } from "@/lib/estimate";
import { clearSavedKeywords } from "@/lib/storage";
import type { AppConfig, SearchJob } from "@/lib/types";

import styles from "./JobSearchPage.module.css";

const PILLS: Record<string, { kind: PillKind; text: string }> = {
  done: { kind: "done", text: "Done" },
  stopped: { kind: "", text: "Stopped" },
  error: { kind: "error", text: "Error" },
};
const CLEAR_QUESTION =
  "Clear the resume, keywords and results from this page?\n\n" +
  "Your settings, applied/hidden jobs, search history and daily search are kept.";

export function JobSearchPage({ config }: { config: AppConfig }) {
  const formApi = useSearchForm(config);
  const { form } = formApi;
  const history = useJobHistory(config.history);
  const daily = useDailySearch();
  const resumeApi = useResume(formApi.fillFromResume);
  const [formError, setFormError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [myJobs, setMyJobs] = useState<{ open: boolean; tab: MyJobsTab }>({ open: false, tab: "applied" });
  const main = useRef<HTMLElement>(null);

  const { refresh, loadStatuses } = history;
  const onFinished = useCallback(
    (job: SearchJob) => {
      void refresh();
      if (job.status === "done") loadStatuses(job.result);
    },
    [loadStatuses, refresh],
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

  const running = search.view === "running";
  const canStart = !!resume && config.has_api_key && !starting;
  const pill = running ? { kind: "running" as const, text: "Searching" } : search.view === "finished" && search.job
    ? PILLS[search.job.status] ?? PILLS.error : { kind: "" as const, text: "Ready" };
  const estimate = estimateSearch({
    sites: chosenSites(form), keywords: form.keywords.length, locations: form.locations,
    maxPages: parseInt(form.maxPages, 10), top: parseInt(form.top, 10), parallel: config.defaults.parallel_sites !== false,
  });

  const startSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    try {
      const request = buildRequest(form, resume?.resume_id);
      formApi.rememberSettings();
      setStarting(true);
      await search.start(request);
      if (window.matchMedia("(max-width: 960px)").matches) main.current?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setStarting(false);
    }
  };

  const saveDaily = () => {
    daily.setError(null);
    try {
      const request = buildRequest(form, resume?.resume_id);
      formApi.rememberSettings();
      void daily.save(request);
    } catch (err) {
      daily.setError((err as Error).message);
    }
  };

  const clearPage = async () => {
    if (!window.confirm(CLEAR_QUESTION)) return;
    try {
      await api.clearSession();
    } catch (err) {
      return setFormError((err as Error).message);
    }
    resumeApi.clear();
    search.reset();
    loadStatuses(null);
    formApi.update({ keywords: [] });
    clearSavedKeywords();
    setFormError(null);
  };

  const forgetSeen = () => history.forgetSeen().catch((err: Error) => setFormError(err.message));
  const setJobStatus = (job: Parameters<typeof history.setStatus>[0], status: Parameters<typeof history.setStatus>[1]) =>
    history.setStatus(job, status).catch((err: Error) => search.setError(err.message));

  return (
    <>
      <Header
        pill={pill} history={history.counts} showClear={!!resume || search.view !== "idle"} clearDisabled={running}
        onClear={clearPage} onOpenMyJobs={() => setMyJobs({ open: true, tab: "applied" })}
      />
      <div className={styles.layout}>
        <form className={styles.setup} noValidate onSubmit={startSearch}>
          {!config.has_api_key ? (
            <Alert message="OPENAI_API_KEY is not set. Add it to your .env file and restart the app." />
          ) : null}
          <ResumeCard resume={resumeApi} />
          <LookForCard form={formApi} locationChoices={config.location_choices} />
          <SitesCard form={formApi} sites={config.sites} />
          <OptionsCard form={formApi} seenCount={history.counts.seen} onForgetSeen={forgetSeen} />
          <DailySearchCard daily={daily} sites={config.sites} canSave={!!resume && config.has_api_key} onSave={saveDaily} />
          <ActionsCard
            estimate={estimate} error={formError} running={running} stopping={search.stopping}
            canStart={canStart} hasResume={!!resume} onStop={search.stop}
          />
        </form>
        <main ref={main}>
          {search.view === "idle" ? <EmptyState /> : (
            <ProgressCard
              job={search.job} view={search.view} restored={search.restored} elapsed={search.elapsed}
              error={search.error} sites={config.sites}
            />
          )}
          {search.view === "finished" && search.job?.status === "done" && search.job.result ? (
            <ResultsCard
              key={search.job.id} result={search.job.result} statuses={history.statuses} onSetStatus={setJobStatus}
            />
          ) : null}
        </main>
      </div>
      <MyJobsSheet
        open={myJobs.open} tab={myJobs.tab} counts={history.counts} sites={config.sites}
        onTab={(tab) => setMyJobs({ open: true, tab })} onClose={() => setMyJobs((s) => ({ ...s, open: false }))}
        onCounts={history.setCounts} onUndo={history.setStatus}
      />
    </>
  );
}
