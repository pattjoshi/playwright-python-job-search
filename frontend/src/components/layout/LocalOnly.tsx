"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useConfig } from "@/providers/ConfigProvider";

/** Online there's no browser to search with: say so instead of showing a page whose buttons can't work. */
export function LocalOnly({ children }: { children: React.ReactNode }) {
  const { config } = useConfig();
  if (!config.hosted) return children;
  return (
    <Alert className="mx-auto mt-10 max-w-xl">
      <AlertTitle>Search runs on your computer</AlertTitle>
      <AlertDescription>
        Searching opens a real browser and takes minutes, which the online version can&apos;t do. Start the app on your computer
        with <code className="font-mono">python -m job_search</code> to search. Online you can use Applications and Notes.
      </AlertDescription>
    </Alert>
  );
}
