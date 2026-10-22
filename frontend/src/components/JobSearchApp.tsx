"use client";

import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { api } from "@/lib/api/endpoints";
import type { AppConfig } from "@/lib/types";

import { JobSearchPage } from "./JobSearchPage";
import styles from "./JobSearchApp.module.css";

/** Loads the settings the page needs from the backend, then shows the page. */
export function JobSearchApp() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.config().then(setConfig).catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className={styles.message}>
        <Alert message="Could not reach the job search app. Is it still running? Start it with: python -m job_search" />
      </div>
    );
  }
  if (!config) return <div className={styles.message} aria-busy="true" />;
  return <JobSearchPage config={config} />;
}
