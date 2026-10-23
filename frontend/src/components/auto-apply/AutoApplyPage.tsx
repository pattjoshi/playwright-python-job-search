"use client";

import { ListPlus, ShieldAlert, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/PageHeader";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAutoApply } from "@/hooks/useAutoApply";
import { autoApplyApi } from "@/lib/api/endpoints";
import type { AutoApplyJob, BoardId } from "@/lib/types";

import { AutoApplyJobRow } from "./AutoApplyJobRow";
import { firstTab, inTab, type QueueTab, TABS } from "./meta";
import { RunCard } from "./RunCard";
import { SettingsCard } from "./SettingsCard";

/** Auto-apply: the queue of matches with a company application page, the run, and the safety settings. */
export function AutoApplyPage() {
  const { data, error, reload } = useAutoApply();
  const [chosenTab, setTab] = useState<QueueTab | null>(null);
  const [busy, setBusy] = useState(false);
  const jobs = useMemo(() => data?.jobs ?? [], [data]);
  const tab = chosenTab ?? firstTab(jobs);
  const shown = jobs.filter((job) => inTab(job, tab));

  const act = async (action: () => Promise<unknown>, done?: string) => {
    setBusy(true);
    try {
      await action();
      if (done) toast.success(done);
      await reload();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const queueLastSearch = () => act(async () => {
    const { added } = await autoApplyApi.queueLastSearch();
    toast(added ? `Added ${added} job${added === 1 ? "" : "s"} from your last search` : "No new matches with a company application page");
  });
  const retry = (job: AutoApplyJob) => act(() => autoApplyApi.retry(job.id), `${job.company} is back in the queue`);
  const remove = (job: AutoApplyJob) => act(() => autoApplyApi.remove(job.id), "Removed");
  const tryJob = (job: AutoApplyJob) => act(() => autoApplyApi.tryJob(job.id), "Trying it now: watch the browser window");
  const signIn = (board: BoardId) =>
    act(() => autoApplyApi.signIn(board), "A browser window opened: sign in there (you have 5 minutes)");
  const running = ["running", "stopping", "signing_in"].includes(data?.run.status ?? "");

  return (
    <>
      <PageHeader
        title="Auto-apply"
        description="Applies to your best matches on company career pages (Greenhouse, Lever, Ashby, SmartRecruiters…) and, if you turn them on, with Easy Apply on Naukri, LinkedIn and Indeed, using your Answer Bank."
        actions={<Button variant="outline" onClick={queueLastSearch} disabled={busy}><ListPlus /> Add matches from last search</Button>}
      />
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {!data && !error ? <Skeleton className="h-64" /> : null}
      {data ? (
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid min-w-0 grid-cols-1 gap-4">
            {data.settings.dry_run ? (
              <Alert>
                <ShieldCheck />
                <AlertTitle>Dry run is on</AlertTitle>
                <AlertDescription>Forms are filled and screenshotted, but nothing is submitted. Check the screenshots, then turn dry run off in Settings.</AlertDescription>
              </Alert>
            ) : (
              <Alert className="border-warning/40 bg-warning-soft">
                <ShieldAlert />
                <AlertTitle>Live: applications are submitted in your name</AlertTitle>
                <AlertDescription>Up to {data.settings.daily_limit} a day, to jobs scoring {data.settings.min_score} or more.</AlertDescription>
              </Alert>
            )}
            <RunCard
              data={data} waiting={jobs.filter((job) => job.status === "queued").length} busy={busy}
              onRun={() => act(() => autoApplyApi.run())} onStop={() => act(() => autoApplyApi.stop())}
            />
            <Tabs value={tab} onValueChange={(value) => setTab(value as QueueTab)}>
              <TabsList className="flex-wrap group-data-[orientation=horizontal]/tabs:h-auto">
                {TABS.map((t) => (
                  <TabsTrigger key={t.id} value={t.id} className="h-8 flex-none">
                    {t.label}
                    <span className="rounded-full bg-background/80 px-1.5 text-xs tabular-nums text-muted-foreground">
                      {jobs.filter((job) => inTab(job, t.id)).length}
                    </span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <ul className="grid grid-cols-1 gap-2">
              {shown.map((job) => <AutoApplyJobRow key={job.id} job={job} onRetry={retry} onTry={tryJob} onRemove={remove} busy={busy || running} />)}
            </ul>
            {!shown.length ? (
              <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">{TABS.find((t) => t.id === tab)!.empty}</p>
            ) : null}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:sticky lg:top-20">
            <SettingsCard
              key={JSON.stringify(data.settings)} settings={data.settings} boards={data.boards} onSaved={() => void reload()}
              onSignIn={signIn} busy={busy || running}
            />
          </div>
        </div>
      ) : null}
    </>
  );
}
