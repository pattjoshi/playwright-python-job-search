"use client";

import { BriefcaseBusiness, Download, Plus } from "lucide-react";
import { useMemo, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useApplications } from "@/hooks/useApplications";
import { applicationsApi } from "@/lib/api/endpoints";
import { loadTrackerView, saveTrackerView } from "@/lib/storage";
import type { Application, ApplicationInput, ApplicationStatus } from "@/lib/types";

import { ApplicationBoard } from "./ApplicationBoard";
import { ApplicationFormDialog } from "./ApplicationFormDialog";
import { ApplicationSheet } from "./ApplicationSheet";
import { ApplicationsToolbar, type TrackerView } from "./ApplicationsToolbar";
import { ApplicationTable } from "./ApplicationTable";
import { matchesQuery, STATUS_BY_ID } from "./statuses";

const noSubscribe = () => () => {};

/** The application tracker: board or table, add/edit dialog, details panel. */
export function ApplicationsPage() {
  const { items, error, reload, create, update, remove } = useApplications();
  // The remembered view is read in the browser only, so the prerendered page (board) and the first render agree.
  const storedView = useSyncExternalStore(noSubscribe, loadTrackerView, () => "board" as const);
  const [chosenView, setView] = useState<TrackerView | null>(null);
  const view = chosenView ?? storedView;
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [editing, setEditing] = useState<Application | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const shown = useMemo(
    () => (items ?? []).filter((app) => matchesQuery(app, query) && (view === "board" || !status || app.status === status)),
    [items, query, status, view],
  );
  const opened = items?.find((app) => app.id === openId) ?? null;

  const changeView = (next: TrackerView) => {
    setView(next);
    saveTrackerView(next);
  };
  const openForm = (app: Application | null) => {
    setEditing(app);
    setFormOpen(true);
  };

  const save = async (input: ApplicationInput) => {
    if (editing) {
      await update(editing.id, input);
      toast.success("Application saved");
    } else {
      const app = await create(input);
      toast.success(`Added ${app.company}`);
    }
  };
  const move = async (app: Application, next: ApplicationStatus) => {
    try {
      await update(app.id, { status: next });
      toast(`${app.company} → ${STATUS_BY_ID[next].label}`);
    } catch (err) {
      toast.error((err as Error).message);
    }
  };
  const destroy = async (app: Application) => {
    try {
      await remove(app.id);
      setOpenId(null);
      toast(`Deleted ${app.company}`);
    } catch (err) {
      toast.error((err as Error).message);
    }
  };
  const importApplied = async () => {
    try {
      const { added } = await applicationsApi.importApplied();
      await reload();
      toast.success(added ? `Imported ${added} applied job${added === 1 ? "" : "s"}` : "No new applied jobs to import");
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  return (
    <>
      <PageHeader
        title="Applications"
        description="Track every job you apply to, from saved to offer."
        actions={
          <>
            <Button variant="outline" onClick={importApplied}><Download /> Import applied jobs</Button>
            <Button onClick={() => openForm(null)}><Plus /> Add application</Button>
          </>
        }
      />
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {!items && !error ? <Skeleton className="h-64" /> : null}
      {items && !items.length ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyMedia variant="icon"><BriefcaseBusiness /></EmptyMedia>
            <EmptyTitle>No applications yet</EmptyTitle>
            <EmptyDescription>
              Add one by hand, press Track on a search result, or import the jobs you already marked as applied.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button onClick={() => openForm(null)}><Plus /> Add application</Button>
          </EmptyContent>
        </Empty>
      ) : null}
      {items?.length ? (
        <>
          <ApplicationsToolbar query={query} onQuery={setQuery} view={view} onView={changeView} status={status} onStatus={setStatus} />
          {view === "board" ? (
            <ApplicationBoard applications={shown} onMove={move} onOpen={(app) => setOpenId(app.id)} />
          ) : (
            <ApplicationTable applications={shown} onOpen={(app) => setOpenId(app.id)} />
          )}
        </>
      ) : null}
      <ApplicationFormDialog open={formOpen} onOpenChange={setFormOpen} application={editing ?? undefined} onSave={save} />
      <ApplicationSheet
        application={opened} onClose={() => setOpenId(null)} onMove={move} onDelete={destroy}
        onEdit={(app) => openForm(app)}
      />
    </>
  );
}
