import { ExternalLink, Image as ImageIcon, RotateCcw, Trash2 } from "lucide-react";
import Link from "next/link";

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { autoApplyApi } from "@/lib/api/endpoints";
import { safeUrl } from "@/lib/format";
import type { AutoApplyJob } from "@/lib/types";

import { PLATFORM_NAMES, STATUS_BADGE } from "./meta";

interface AutoApplyJobRowProps {
  job: AutoApplyJob;
  onRetry: (job: AutoApplyJob) => void;
  onRemove: (job: AutoApplyJob) => void;
}

/** One job: what happened, what was put in the form, the screenshot, and retry / remove. */
export function AutoApplyJobRow({ job, onRetry, onRemove }: AutoApplyJobRowProps) {
  const badge = STATUS_BADGE[job.status];
  const company = safeUrl(job.apply_url);
  const posting = safeUrl(job.job_url);
  const canRetry = !["queued", "running", "submitted"].includes(job.status);
  return (
    <li className="grid grid-cols-1 gap-2 rounded-lg border bg-card p-4" aria-label={`${job.title} at ${job.company}`}>
      <div className="flex flex-wrap items-center gap-2">
        <p className="min-w-0 font-medium break-words">{job.title} <span className="font-normal text-muted-foreground">· {job.company}</span></p>
        <Badge variant="secondary" className={badge.className}>{badge.label}</Badge>
        <Badge variant="outline">{PLATFORM_NAMES[job.platform] ?? job.platform}</Badge>
        {job.score !== null ? <span className="text-xs text-muted-foreground tabular-nums">Match {job.score}</span> : null}
      </div>
      {job.message ? <p className="text-sm break-words">{job.message}</p> : null}
      {job.status === "needs_answer" ? (
        <p className="text-sm"><Link href="/answers" className="font-medium text-primary hover:underline">Answer it in the Answer Bank</Link>, then press Retry.</p>
      ) : null}
      {job.answers.length ? (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">What was filled in ({job.answers.length})</summary>
          <dl className="mt-2 grid grid-cols-1 gap-1.5">
            {job.answers.map((a) => (
              <div key={a.question} className="grid grid-cols-1 gap-0.5 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] sm:gap-3">
                <dt className="text-muted-foreground break-words">{a.question}</dt>
                <dd className="break-words whitespace-pre-wrap">{a.answer}</dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}
      {job.cover_letter ? (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">Cover letter</summary>
          <p className="mt-2 whitespace-pre-wrap">{job.cover_letter}</p>
        </details>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {job.screenshot ? (
          <Button asChild variant="outline" size="sm">
            <a href={autoApplyApi.screenshotUrl(job.id, job.updated_at)} target="_blank" rel="noopener noreferrer"><ImageIcon /> Screenshot</a>
          </Button>
        ) : null}
        {company ? <Button asChild variant="outline" size="sm"><a href={company} target="_blank" rel="noopener noreferrer">Application page <ExternalLink /></a></Button> : null}
        {posting ? <Button asChild variant="ghost" size="sm"><a href={posting} target="_blank" rel="noopener noreferrer">Job posting <ExternalLink /></a></Button> : null}
        {canRetry ? <Button variant="outline" size="sm" onClick={() => onRetry(job)}><RotateCcw /> {job.status === "filled" ? "Apply again" : "Retry"}</Button> : null}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive" aria-label={`Remove ${job.title} at ${job.company}`}>
              <Trash2 /> Remove
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove this job?</AlertDialogTitle>
              <AlertDialogDescription>{job.title} at {job.company} leaves the auto-apply list, with its screenshot.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => onRemove(job)}>Remove</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </li>
  );
}
