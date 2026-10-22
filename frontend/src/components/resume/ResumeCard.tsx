"use client";

import { useRef, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHead } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import type { ResumeApi } from "@/hooks/useResume";

import styles from "./ResumeCard.module.css";

const ACCEPT = ".pdf,.docx,.txt,.md";

/** Step 1: drop or pick a resume; shows what the AI read from it. */
export function ResumeCard({ resume: state }: { resume: ResumeApi }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const { resume, restored, analyzing, error, analyze } = state;

  const pick = (files: FileList | null) => {
    if (files?.[0]) void analyze(files[0]);
  };
  const dragProps = {
    onDragEnter: (e: React.DragEvent) => { e.preventDefault(); setOver(true); },
    onDragOver: (e: React.DragEvent) => { e.preventDefault(); setOver(true); },
    onDragLeave: (e: React.DragEvent) => { e.preventDefault(); setOver(false); },
    onDrop: (e: React.DragEvent) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files); },
  };
  const profile = resume?.profile;
  const years = profile?.years_experience != null ? `${+profile.years_experience.toFixed(1)} yrs experience` : "";
  const extension = (resume?.file_name.split(".").pop() ?? "").toUpperCase().slice(0, 4);

  return (
    <Card>
      <CardBody>
        <CardHead step={1} done={!!resume}>Resume</CardHead>
        <label className={[styles.drop, over ? styles.over : ""].join(" ")} hidden={!!resume || analyzing} {...dragProps}>
          <input
            ref={input} type="file" accept={ACCEPT} aria-describedby="drop-hint"
            onChange={(e) => { pick(e.target.files); e.target.value = ""; }}
          />
          <strong>Drop your resume here, or click to browse</strong>
          <span id="drop-hint">PDF, DOCX or TXT · stays on your computer</span>
        </label>
        {analyzing ? (
          <div className={styles.analyzing}><Spinner />Reading your resume with AI…</div>
        ) : null}
        {resume && profile ? (
          <div>
            <div className={styles.ready}>
              <div className={styles.fileIcon}>{extension}</div>
              <div className={styles.meta}>
                <div className={styles.name}>{resume.file_name}</div>
                <div className={styles.sub}>{[profile.current_title, years].filter(Boolean).join(" · ")}</div>
              </div>
              <Button onClick={() => input.current?.click()}>Replace</Button>
            </div>
            <p className={styles.summary}>{profile.summary}</p>
            {restored ? <p className={styles.restored}>✓ Restored from your last session · no upload or AI call needed</p> : null}
          </div>
        ) : null}
        <Alert message={error} className={styles.error} />
      </CardBody>
    </Card>
  );
}
