"use client";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useConfig } from "@/providers/ConfigProvider";
import { useSearchSession } from "@/providers/SearchSessionProvider";

import { AccountCard } from "./AccountCard";
import { AppearanceCard } from "./AppearanceCard";
import { OpenAIKeyCard } from "./OpenAIKeyCard";

const DATA_FOLDERS = [
  ["uploads/", "Resumes you uploaded"],
  ["output/", "HTML / Excel / CSV reports"],
  ["data/history.sqlite3", "Applied, hidden and seen jobs, and the search history"],
  ["data/cache.sqlite3", "Saved job details, AI scores and resume readings (safe to delete)"],
  ["data/secrets.json", "Your OpenAI key, encrypted (the key to read it: data/secret.key, or APP_SECRET)"],
  [".env", "Your settings"],
];

export function SettingsPage() {
  const { config } = useConfig();
  const { history, forgetSeen } = useSearchSession();
  return (
    <>
      <PageHeader title="Settings" description="Your account, appearance, AI key and where your data lives." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <AccountCard />
        <AppearanceCard />
        {config.hosted ? null : <OpenAIKeyCard />}
        {config.hosted ? null : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Seen jobs</CardTitle>
                <CardDescription>With “Only new jobs” on, jobs you were already shown are skipped.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-3 text-sm">
                <span>{history.counts.seen ? `${history.counts.seen} jobs marked as seen.` : "No seen jobs yet."}</span>
                <Button variant="outline" size="sm" disabled={!history.counts.seen} onClick={forgetSeen}>Forget seen jobs</Button>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Your data</CardTitle>
                <CardDescription>Everything stays in the project folder on this computer.</CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-1 gap-2 text-sm">
                  {DATA_FOLDERS.map(([path, what]) => (
                    <div key={path} className="grid grid-cols-[minmax(0,11rem)_1fr] gap-3">
                      <dt className="truncate font-mono text-xs leading-5">{path}</dt>
                      <dd className="text-muted-foreground">{what}</dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          </>
        )}
      </div>
      <p className="mt-6 text-xs text-muted-foreground">Job Search {config.version ? `v${config.version}` : ""}</p>
    </>
  );
}
