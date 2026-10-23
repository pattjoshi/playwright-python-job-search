"use client";

import { BriefcaseBusiness, Eraser } from "lucide-react";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import type { HistoryCounts } from "@/lib/types";
import { cn } from "@/lib/utils";

export type PillKind = "" | "running" | "done" | "error";

interface SearchToolbarProps {
  pill: { kind: PillKind; text: string };
  history: HistoryCounts;
  showClear: boolean;
  clearDisabled: boolean;
  onClear: () => void;
  onOpenMyJobs: () => void;
}

const PILL_STYLES: Record<PillKind, string> = {
  "": "bg-muted text-muted-foreground",
  running: "bg-accent text-accent-foreground",
  done: "bg-success-soft text-success",
  error: "bg-destructive/10 text-destructive",
};

/** Status of the search, plus Clear and My jobs. */
export function SearchToolbar({ pill, history, showClear, clearDisabled, onClear, onOpenMyJobs }: SearchToolbarProps) {
  const counts = [history.applied ? `${history.applied} applied` : "", history.hidden ? `${history.hidden} hidden` : ""]
    .filter(Boolean).join(" · ");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold", PILL_STYLES[pill.kind])} aria-live="polite">
        <span className="size-1.5 rounded-full bg-current" />{pill.text}
      </span>
      {showClear ? (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm" disabled={clearDisabled} title="Remove the resume, keywords and results from this page">
              <Eraser /> Clear
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear this page?</AlertDialogTitle>
              <AlertDialogDescription>
                This removes the resume, keywords and results from the page. Your settings, applied/hidden jobs,
                search history and daily search are kept.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onClear}>Clear page</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ) : null}
      <Button variant="outline" size="sm" aria-haspopup="dialog" onClick={onOpenMyJobs}>
        <BriefcaseBusiness /> My jobs {counts ? <span className="font-normal text-muted-foreground max-sm:hidden">· {counts}</span> : null}
      </Button>
    </div>
  );
}
