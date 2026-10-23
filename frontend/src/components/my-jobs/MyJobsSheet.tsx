"use client";

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { HistoryCounts, JobStatus, SavedJob, SiteConfig } from "@/lib/types";

import { RunsList } from "./RunsList";
import { SavedJobsList } from "./SavedJobsList";

export type MyJobsTab = "applied" | "hidden" | "runs";

interface MyJobsSheetProps {
  open: boolean;
  tab: MyJobsTab;
  onTab: (tab: MyJobsTab) => void;
  onClose: () => void;
  counts: HistoryCounts;
  sites: SiteConfig[];
  onCounts: (counts: HistoryCounts) => void;
  onUndo: (job: SavedJob, status: JobStatus) => Promise<unknown>;
}

/** Side panel with your applied and hidden jobs, and the history of searches. */
export function MyJobsSheet({ open, tab, onTab, onClose, counts, sites, onCounts, onUndo }: MyJobsSheetProps) {
  const names = Object.fromEntries(sites.map((site) => [site.id, site.name]));
  const count = (n: number) => <span className="rounded-full bg-muted px-1.5 text-xs text-muted-foreground tabular-nums">{n}</span>;
  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader className="border-b">
          <SheetTitle>My jobs</SheetTitle>
          <SheetDescription>Jobs you applied to or hid, and every search you ran.</SheetDescription>
        </SheetHeader>
        <Tabs value={tab} onValueChange={(value) => onTab(value as MyJobsTab)} className="gap-0">
          <div className="border-b px-4 py-2.5">
            <TabsList>
              <TabsTrigger value="applied">Applied {count(counts.applied)}</TabsTrigger>
              <TabsTrigger value="hidden">Hidden {count(counts.hidden)}</TabsTrigger>
              <TabsTrigger value="runs">Search history</TabsTrigger>
            </TabsList>
          </div>
        </Tabs>
        <ul className="m-0 flex-1 list-none overflow-auto p-0">
          {open && tab !== "runs" ? <SavedJobsList key={tab} status={tab} names={names} onCounts={onCounts} onUndo={onUndo} /> : null}
          {open && tab === "runs" ? <RunsList sites={sites} /> : null}
        </ul>
      </SheetContent>
    </Sheet>
  );
}
