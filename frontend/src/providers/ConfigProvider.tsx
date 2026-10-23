"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { ShellSkeleton } from "@/components/layout/ShellSkeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { api } from "@/lib/api/endpoints";
import type { AppConfig } from "@/lib/types";

interface ConfigContextValue {
  config: AppConfig;
  refresh: () => Promise<void>;
}

const ConfigContext = createContext<ConfigContextValue | null>(null);

/** Loads the backend's settings once for the whole app; children render after it arrives. */
export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [failed, setFailed] = useState(false);

  const refresh = useCallback(async () => setConfig(await api.config()), []);

  useEffect(() => {
    api.config().then(setConfig).catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="mx-auto mt-16 max-w-xl px-4">
        <Alert variant="destructive">
          <AlertTitle>Could not reach the job search app</AlertTitle>
          <AlertDescription>Is it still running? Start it with: python -m job_search</AlertDescription>
        </Alert>
      </div>
    );
  }
  if (!config) return <ShellSkeleton />;
  return <ConfigContext.Provider value={{ config, refresh }}>{children}</ConfigContext.Provider>;
}

export function useConfig(): ConfigContextValue {
  const value = useContext(ConfigContext);
  if (!value) throw new Error("useConfig must be used inside <ConfigProvider>");
  return value;
}
