"use client";

import { Search } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { useRuns } from "@/hooks/useRuns";
import { useSearchSession } from "@/providers/SearchSessionProvider";

import { ComingNextCard } from "./ComingNextCard";
import { CurrentSearchCard } from "./CurrentSearchCard";
import { DailySummaryCard } from "./DailySummaryCard";
import { RecentRunsCard } from "./RecentRunsCard";
import { StatCards } from "./StatCards";

export function DashboardPage() {
  const { history, search } = useSearchSession();
  // Reload the search history whenever a search finishes.
  const { runs, error } = useRuns(search.view === "finished" ? search.job?.id : null);
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Your job search at a glance."
        actions={<Button asChild><Link href="/search"><Search /> Search jobs</Link></Button>}
      />
      <div className="grid grid-cols-1 gap-4">
        <StatCards counts={history.counts} searches={runs ? (runs.length >= 50 ? "50+" : runs.length) : null} />
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="grid min-w-0 grid-cols-1 content-start gap-4">
            <CurrentSearchCard />
            <RecentRunsCard runs={runs} error={error} />
          </div>
          <div className="grid min-w-0 grid-cols-1 content-start gap-4">
            <DailySummaryCard />
            <ComingNextCard />
          </div>
        </div>
      </div>
    </>
  );
}
