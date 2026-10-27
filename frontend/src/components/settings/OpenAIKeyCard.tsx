"use client";

import { CheckCircle2, KeyRound, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/providers/AuthProvider";
import { openAIKeyApi, type OpenAIKeyStatus } from "@/lib/api/endpoints";
import { useConfig } from "@/providers/ConfigProvider";

const SOURCE_TEXT = { settings: "Your key, saved here", env: "Key from the .env file" };

/** Save your own OpenAI key: checked with OpenAI first, stored encrypted on this computer, never shown again. */
export function OpenAIKeyCard() {
  const { refresh } = useConfig();
  const { user } = useAuth();
  const [status, setStatus] = useState<OpenAIKeyStatus | null>(null);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    openAIKeyApi.get().then(setStatus, () => undefined);
  }, []);

  const run = async (action: () => Promise<OpenAIKeyStatus>, done: string) => {
    setBusy(true);
    try {
      setStatus(await action());
      setKey("");
      await refresh(); // the Search page's "add a key" notice follows at once
      toast.success(done);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const owner = user?.role === "owner";
  return (
    <Card>
      <CardHeader>
        <CardTitle>OpenAI key</CardTitle>
        <CardDescription>
          Reads your resume, scores jobs and writes answers. Get one at{" "}
          <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
            platform.openai.com/api-keys
          </a>.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 text-sm">
        {status?.source ? (
          <p className="flex items-center gap-2 text-success" role="status">
            <CheckCircle2 className="size-4" /> {SOURCE_TEXT[status.source]} <span className="font-mono text-xs">{status.hint}</span>
          </p>
        ) : status ? (
          <p className="flex items-center gap-2 text-destructive" role="status"><TriangleAlert className="size-4" /> No key yet: add yours below.</p>
        ) : null}
        {owner ? (
          <form
            className="flex flex-wrap gap-2" onSubmit={(e) => {
              e.preventDefault();
              if (key.trim()) void run(() => openAIKeyApi.save(key), "Key checked with OpenAI and saved");
            }}
          >
            <Input
              type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="sk-…" aria-label="OpenAI key"
              autoComplete="off" spellCheck={false} className="min-w-48 flex-1 font-mono"
            />
            <Button type="submit" disabled={busy || !key.trim()}><KeyRound /> {busy ? "Checking…" : "Save key"}</Button>
            {status?.source === "settings" ? (
              <Button variant="ghost" disabled={busy} onClick={() => void run(openAIKeyApi.remove, "Key removed")}>Remove</Button>
            ) : null}
          </form>
        ) : (
          <p className="text-muted-foreground">Only the owner of this app can change the key.</p>
        )}
        <p className="text-xs text-muted-foreground">
          Saved encrypted in <span className="font-mono">data/secrets.json</span> and never shown again. A key saved here is
          used instead of the one in .env, right away and by the daily search.
        </p>
      </CardContent>
    </Card>
  );
}
