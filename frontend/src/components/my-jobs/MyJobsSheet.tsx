"use client";

import { Sheet } from "@/components/ui/Sheet";
import { Tabs } from "@/components/ui/Tabs";
import type { HistoryCounts, JobStatus, SavedJob, SiteConfig } from "@/lib/types";

import { RunsList } from "./RunsList";
import { SavedJobsList } from "./SavedJobsList";
import styles from "./MyJobsSheet.module.css";

export type MyJobsTab = "applied" | "hidden" | "runs";

interface MyJobsSheetProps {
  open: boolean;
  tab: MyJobsTab;
  onTab: (tab: MyJobsTab) => void;
  onClose: () => void;
  counts: HistoryCounts;
  sites: SiteConfig[];
  onCounts: (counts: HistoryCounts) => void;
  onUndo: (job: SavedJob, status: JobStatus) => Promise<void>;
}

/** Side panel with your applied and hidden jobs, and the history of searches. */
export function MyJobsSheet({ open, tab, onTab, onClose, counts, sites, onCounts, onUndo }: MyJobsSheetProps) {
  const names = Object.fromEntries(sites.map((site) => [site.id, site.name]));
  const tabs = [
    { id: "applied", name: "Applied", count: counts.applied },
    { id: "hidden", name: "Hidden", count: counts.hidden },
    { id: "runs", name: "Search history" },
  ];
  return (
    <Sheet open={open} title="My jobs" onClose={onClose}>
      <Tabs tabs={tabs} selected={tab} onSelect={(id) => onTab(id as MyJobsTab)} className={styles.tabs} />
      <ul className={styles.list}>
        {open && tab !== "runs" ? (
          <SavedJobsList key={tab} status={tab} names={names} onCounts={onCounts} onUndo={onUndo} />
        ) : null}
        {open && tab === "runs" ? <RunsList sites={sites} /> : null}
      </ul>
    </Sheet>
  );
}
