"use client";

import { FileUp } from "lucide-react";
import { useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StepTitle } from "@/components/ui/step-title";
import type { ResumeApi } from "@/hooks/useResume";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.docx,.txt,.md";

/** Step 1: drop or pick a resume; shows what the AI read from it. */
export function ResumeCard({ resume: state }: { resume: ResumeApi }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const { resume, restored, analyzing, error, analyze } = state;

  const pick = (files: FileList | null) => {
    if (files?.[0]) void analyze(files[0]);
  };
  const drag = (active: boolean) => (e: React.DragEvent) => {
    e.preventDefault();
    setOver(active);
  };
  const profile = resume?.profile;
  const years = profile?.years_experience != null ? `${+profile.years_experience.toFixed(1)} yrs experience` : "";
  const extension = (resume?.file_name.split(".").pop() ?? "").toUpperCase().slice(0, 4);

  return (
    <Card className="gap-4 py-5">
      <CardContent className="grid grid-cols-1 gap-3 px-5">
        <StepTitle step={1} done={!!resume}>Resume</StepTitle>
        <label
          hidden={!!resume || analyzing} onDragEnter={drag(true)} onDragOver={drag(true)} onDragLeave={drag(false)}
          onDrop={(e) => { drag(false)(e); pick(e.dataTransfer.files); }}
          className={cn(
            "relative block cursor-pointer rounded-lg border-[1.5px] border-dashed border-input bg-muted/40 px-4 py-6 text-center transition-colors",
            "hover:border-primary hover:bg-accent focus-within:ring-[3px] focus-within:ring-ring/50", over && "border-primary bg-accent",
          )}
        >
          <input
            ref={input} type="file" accept={ACCEPT} aria-describedby="drop-hint" className="sr-only"
            onChange={(e) => { pick(e.target.files); e.target.value = ""; }}
          />
          <FileUp className="mx-auto mb-2 size-6 text-primary" aria-hidden="true" />
          <strong className="block text-sm">Drop your resume here, or click to browse</strong>
          <span id="drop-hint" className="text-xs text-muted-foreground">PDF, DOCX or TXT · stays on your computer</span>
        </label>
        {analyzing ? (
          <div className="flex items-center gap-2.5 py-3 text-sm text-muted-foreground"><Spinner />Reading your resume with AI…</div>
        ) : null}
        {resume && profile ? (
          <div className="grid grid-cols-1 gap-2">
            <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-3">
              <div className="grid grid-cols-1 h-10 w-9 shrink-0 place-items-center rounded-md bg-accent text-[11px] font-extrabold text-accent-foreground">
                {extension}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">{resume.file_name}</div>
                <div className="text-xs text-muted-foreground">{[profile.current_title, years].filter(Boolean).join(" · ")}</div>
              </div>
              <Button variant="outline" size="sm" onClick={() => input.current?.click()}>Replace</Button>
            </div>
            <p className="text-sm text-muted-foreground">{profile.summary}</p>
            {restored ? <p className="text-xs text-success">✓ Restored from your last session · no upload or AI call needed</p> : null}
          </div>
        ) : null}
        {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
      </CardContent>
    </Card>
  );
}
