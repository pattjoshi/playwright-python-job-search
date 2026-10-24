import { ExternalLink, PanelRightOpen } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChipRow } from "@/components/ui/chip";
import { safeUrl, scoreBand } from "@/lib/format";
import type { Job, JobStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

import { TrackButton } from "./TrackButton";

interface JobCardProps {
  job: Job;
  rank: number;
  applied: boolean;
  siteName?: string;
  onSetStatus: (status: JobStatus) => void;
  onDetails: () => void;
}

const BANDS = { good: "bg-success-soft text-success", ok: "bg-warning-soft text-warning", low: "bg-muted text-muted-foreground" };

/** One job: match score, title and links, matching/missing skills, the AI's reason, and actions. */
export function JobCard({ job, rank, applied, siteName, onSetStatus, onDetails }: JobCardProps) {
  const url = safeUrl(job.url) ?? "#";
  return (
    <li className={cn("grid grid-cols-[52px_minmax(0,1fr)] gap-3.5 border-t px-5 py-4 transition-opacity first:border-t-0 max-sm:grid-cols-1", applied && "opacity-60")}>
      <div className="max-sm:flex max-sm:items-center max-sm:gap-2.5">
        <div className={cn("grid size-12 place-items-center rounded-full text-base font-extrabold", BANDS[scoreBand(job.score)])} title="Match score">
          {job.score ?? "–"}
        </div>
        <div className="mt-1 text-center text-[11px] text-muted-foreground max-sm:mt-0">#{rank}</div>
      </div>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-[15px] font-bold text-primary hover:underline">{job.title}</a>
          {job.is_new ? <Badge className="bg-new-soft text-new">New</Badge> : null}
          {applied ? <Badge className="bg-success-soft text-success">Applied</Badge> : null}
          {siteName ? <Badge variant="secondary">{siteName}</Badge> : null}
          {job.apply_url ? (
            <Badge variant="outline" title="Applied to on the company's own career page: auto-apply can do this one">Company site</Badge>
          ) : null}
        </div>
        <div className="mt-0.5 mb-1.5 text-sm text-muted-foreground">
          {[job.company, job.location, job.experience, job.posted_text].filter(Boolean).join(" · ")}
        </div>
        <ChipRow label="Matching" items={job.matched_skills ?? []} kind="have" />
        <ChipRow label="Missing" items={job.missing_skills ?? []} kind="miss" />
        {job.match_reason ? <p className="mt-1.5 text-sm">{job.match_reason}</p> : null}
        <div className="mt-2.5 flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={onDetails}><PanelRightOpen /> Details</Button>
          <Button asChild variant="outline" size="sm">
            <a href={url} target="_blank" rel="noopener noreferrer">View job <ExternalLink /></a>
          </Button>
          {applied ? (
            <Button variant="outline" size="sm" onClick={() => onSetStatus("seen")}>Undo applied</Button>
          ) : (
            <>
              <TrackButton job={job} />
              <Button variant="outline" size="sm" onClick={() => onSetStatus("applied")}>✓ Mark applied</Button>
              <Button variant="ghost" size="sm" onClick={() => onSetStatus("hidden")}>Hide</Button>
            </>
          )}
        </div>
      </div>
    </li>
  );
}

export function HiddenJob({ job, onUndo }: { job: Job; onUndo: () => void }) {
  return (
    <li className="flex gap-2.5 border-t px-5 py-3 text-sm text-muted-foreground first:border-t-0">
      Hidden “{job.title}”
      <Button variant="link" size="xs" className="h-auto p-0" onClick={onUndo}>Undo</Button>
    </li>
  );
}
