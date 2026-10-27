"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { authApi } from "@/lib/api/endpoints";

import { AuthForm } from "./AuthForm";
import { nextUrl } from "./next-url";

const TEXT = {
  setup: {
    title: "Create your account",
    description: "First time here: this account protects your resume, jobs and history on this computer.",
  },
  signin: { title: "Welcome back", description: "Sign in to continue your job search." },
};

/** /login: sign in, or create the first account. Already signed in? Goes straight on. */
export function LoginPage() {
  const [mode, setMode] = useState<"setup" | "signin" | null>(null);
  const [failed, setFailed] = useState(false);
  const [needsCode, setNeedsCode] = useState(false);

  useEffect(() => {
    authApi.status()
      .then((status) => {
        if (status.user) window.location.replace(nextUrl());
        else setMode(status.setup_required ? "setup" : "signin");
        setNeedsCode(!!status.setup_code_required);
      })
      .catch(() => setFailed(true));
  }, []);

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-background px-4 py-10">
      <Link href="/" className="flex items-center gap-2.5">
        <span className="grid size-9 place-items-center rounded-lg bg-primary text-base font-bold text-primary-foreground">J</span>
        <span className="text-lg font-bold">Job Search</span>
      </Link>
      <Card className="w-full max-w-sm">
        {failed ? (
          <CardContent className="text-sm text-destructive">Could not reach the app. Is it still running? Start it with: python -m job_search</CardContent>
        ) : !mode ? (
          <CardContent className="grid grid-cols-1 gap-3" aria-busy="true">
            <Skeleton className="h-6 w-40" /><Skeleton className="h-9" /><Skeleton className="h-9" /><Skeleton className="h-10" />
          </CardContent>
        ) : (
          <>
            <CardHeader>
              <CardTitle className="text-xl">{TEXT[mode].title}</CardTitle>
              <CardDescription>{TEXT[mode].description}</CardDescription>
            </CardHeader>
            <CardContent>
              <AuthForm mode={mode} needsCode={needsCode} onDone={() => window.location.replace(nextUrl())} />
            </CardContent>
          </>
        )}
      </Card>
      {mode === "signin" ? (
        <p className="max-w-sm text-center text-xs text-muted-foreground">
          Forgot your password? In the project folder run <code className="font-mono">python -m job_search reset-password --email you@example.com</code>
        </p>
      ) : null}
    </div>
  );
}
