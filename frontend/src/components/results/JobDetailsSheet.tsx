"use client";

import { EyeOff, ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChipRow } from "@/components/ui/chip";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { safeUrl } from "@/lib/format";
import { postedAgo } from "@/lib/results-filter";
import type { Job, JobStatus } from "@/lib/types";

import { TrackButton } from "./TrackButton";

interface JobDetailsSheetProps {
  job: Job | null;
  siteName?: string;
  applied: boolean;
  onClose: () => void;
  onSetStatus: (job: Job, status: JobStatus) => void;
  onHideCompany: (job: Job) => void;
}

/** Everything the search found about one job, read without leaving the page. */
export function JobDetailsSheet({ job, siteName, applied, onClose, onSetStatus, onHideCompany }: JobDetailsSheetProps) {
  const url = job ? safeUrl(job.url) : null;
  const facts: [string, string][] = job ? [
    ["Location", job.location], ["Experience", job.experience], ["Posted", postedAgo(job.hours_ago) || job.posted_text || ""],
    ["Match score", job.score == null ? "" : String(job.score)], ["Site", siteName ?? job.source],
  ] : [];
  return (
    <Sheet open={!!job} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-xl">
        {job ? (
          <>
            <SheetHeader className="border-b">
              <SheetTitle className="pr-6">{job.title}</SheetTitle>
              <SheetDescription>{job.company}</SheetDescription>
            </SheetHeader>
            <div className="grid grid-cols-1 gap-5 p-4">
              <div className="flex flex-wrap gap-2">
                {url ? (
                  <Button asChild size="sm"><a href={url} target="_blank" rel="noopener noreferrer">View job <ExternalLink /></a></Button>
                ) : null}
                <TrackButton job={job} />
                {applied ? (
                  <Button variant="outline" size="sm" onClick={() => onSetStatus(job, "seen")}>Undo applied</Button>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => onSetStatus(job, "applied")}>✓ Mark applied</Button>
                )}
                <Button variant="ghost" size="sm" onClick={() => onHideCompany(job)}><EyeOff /> Hide this company</Button>
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {facts.filter(([, value]) => value).map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="break-words">{value}</dd>
                  </div>
                ))}
              </dl>
              {job.match_reason ? (
                <div>
                  <h4 className="mb-1 text-xs text-muted-foreground">Why it matches</h4>
                  <p className="text-sm">{job.match_reason}</p>
                </div>
              ) : null}
              <div className="grid grid-cols-1 gap-1">
                <ChipRow label="Matching" items={job.matched_skills ?? []} kind="have" />
                <ChipRow label="Missing" items={job.missing_skills ?? []} kind="miss" />
              </div>
              <div>
                <h4 className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
                  Job description
                </h4>
                {job.description ? (
                  <p className="text-sm leading-relaxed break-words whitespace-pre-wrap">{job.description}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">No description was read for this job. Open it on the site to see the full posting.</p>
                )}
              </div>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
