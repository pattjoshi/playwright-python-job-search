"use client";

import { useCallback, useState } from "react";

import { api } from "@/lib/api/endpoints";
import type { Resume } from "@/lib/types";

/** The uploaded resume and the AI's reading of it. */
export function useResume(onAnalyzed: (resume: Resume) => void) {
  const [resume, setResume] = useState<Resume | null>(null);
  const [restored, setRestored] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(
    async (file: File) => {
      setError(null);
      setResume(null);
      setRestored(false);
      setAnalyzing(true);
      try {
        const body = await api.analyzeResume(file);
        setResume(body);
        onAnalyzed(body);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setAnalyzing(false);
      }
    },
    [onAnalyzed],
  );

  /** The resume from before a reload or restart: shown again without uploading or an AI call. */
  const restore = useCallback((saved: Resume) => {
    setResume(saved);
    setRestored(true);
  }, []);

  const clear = useCallback(() => {
    setResume(null);
    setRestored(false);
    setError(null);
  }, []);

  return { resume, restored, analyzing, error, analyze, restore, clear };
}

export type ResumeApi = ReturnType<typeof useResume>;
