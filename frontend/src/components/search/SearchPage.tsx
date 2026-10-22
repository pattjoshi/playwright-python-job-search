"use client";

import { useRef, useState } from "react";

import { DailySearchCard } from "@/components/daily/DailySearchCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { MyJobsSheet, type MyJobsTab } from "@/components/my-jobs/MyJobsSheet";
import { ProgressCard } from "@/components/progress/ProgressCard";
import { ResumeCard } from "@/components/resume/ResumeCard";
import { EmptyState } from "@/components/results/EmptyState";
import { ResultsCard } from "@/components/results/ResultsCard";
import { ActionsCard } from "@/components/search-form/ActionsCard";
import { LookForCard } from "@/components/search-form/LookForCard";
import { OptionsCard } from "@/components/search-form/OptionsCard";
import { SitesCard } from "@/components/search-form/SitesCard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { chosenSites } from "@/hooks/useSearchForm";
import { estimateSearch } from "@/lib/estimate";
import { useConfig } from "@/providers/ConfigProvider";
import { useSearchSession } from "@/providers/SearchSessionProvider";

import { type PillKind, SearchToolbar } from "./SearchToolbar";

const PILLS: Record<string, { kind: PillKind; text: string }> = {
  done: { kind: "done", text: "Done" },
  stopped: { kind: "", text: "Stopped" },
  error: { kind: "error", text: "Error" },
};

/** Set up a search on the left; watch it run and read the ranked results on the right. */
export function SearchPage() {
  const { config } = useConfig();
  const session = useSearchSession();
  const { formApi, history, daily, resumeApi, search } = session;
  const { form } = formApi;
  const [myJobs, setMyJobs] = useState<{ open: boolean; tab: MyJobsTab }>({ open: false, tab: "applied" });
  const main = useRef<HTMLElement>(null);

  const running = search.view === "running";
  const pill = running ? { kind: "running" as const, text: "Searching" }
    : search.view === "finished" && search.job ? PILLS[search.job.status] ?? PILLS.error : { kind: "" as const, text: "Ready" };
  const estimate = estimateSearch({
    sites: chosenSites(form), keywords: form.keywords.length, locations: form.locations,
    maxPages: parseInt(form.maxPages, 10), top: parseInt(form.top, 10), parallel: config.defaults.parallel_sites !== false,
  });

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const started = await session.startSearch();
    if (started && window.matchMedia("(max-width: 1023px)").matches) main.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <>
      <PageHeader
        title="Search jobs"
        description="Upload your resume, pick what to look for, and get the best recent jobs ranked by AI."
        actions={
          <SearchToolbar
            pill={pill} history={history.counts} showClear={!!resumeApi.resume || search.view !== "idle"} clearDisabled={running}
            onClear={session.clearPage} onOpenMyJobs={() => setMyJobs({ open: true, tab: "applied" })}
          />
        }
      />
      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[400px_minmax(0,1fr)]">
        <form className="grid grid-cols-1 gap-3.5" noValidate onSubmit={onSubmit}>
          {!config.has_api_key ? (
            <Alert variant="destructive"><AlertDescription>OPENAI_API_KEY is not set. Add it to your .env file and restart the app.</AlertDescription></Alert>
          ) : null}
          <ResumeCard resume={resumeApi} />
          <LookForCard form={formApi} locationChoices={config.location_choices} />
          <SitesCard form={formApi} sites={config.sites} />
          <OptionsCard form={formApi} seenCount={history.counts.seen} onForgetSeen={session.forgetSeen} />
          <DailySearchCard daily={daily} sites={config.sites} canSave={!!resumeApi.resume && config.has_api_key} onSave={session.saveDaily} />
          <ActionsCard
            estimate={estimate} error={session.formError} running={running} stopping={search.stopping} starting={session.starting}
            canStart={session.canStart} hasResume={!!resumeApi.resume} onStop={search.stop}
          />
        </form>
        <main ref={main} className="scroll-mt-20">
          {search.view === "idle" ? <EmptyState /> : (
            <ProgressCard
              job={search.job} view={search.view} restored={search.restored} elapsed={search.elapsed}
              error={search.error} sites={config.sites}
            />
          )}
          {search.view === "finished" && search.job?.status === "done" && search.job.result ? (
            <ResultsCard key={search.job.id} result={search.job.result} statuses={history.statuses} onSetStatus={session.setJobStatus} />
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
