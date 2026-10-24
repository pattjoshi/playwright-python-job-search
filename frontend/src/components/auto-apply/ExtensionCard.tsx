"use client";

import { Copy, Puzzle, Unplug } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { autoApplyApi } from "@/lib/api/endpoints";
import { formatDateTime } from "@/lib/format";
import type { AutoApplyOverview } from "@/lib/types";

/** Connect the Chrome extension, which applies in your own Chrome (already signed in to the boards). */
export function ExtensionCard({ extension, onChange }: { extension: AutoApplyOverview["extension"]; onChange: () => void }) {
  const [key, setKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const connect = async () => {
    setBusy(true);
    try {
      setKey((await autoApplyApi.extensionKey()).key);
      onChange();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const disconnect = async () => {
    await autoApplyApi.disconnectExtension().catch((err: Error) => toast.error(err.message));
    setKey(null);
    onChange();
  };
  const copy = async () => {
    if (!key) return;
    await navigator.clipboard.writeText(key).then(() => toast.success("Key copied"), () => toast.error("Couldn't copy: select it and copy"));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Puzzle className="size-4" /> Chrome extension</CardTitle>
        <CardDescription>
          Easy Apply in your own Chrome, where you&apos;re already signed in to Naukri, LinkedIn and Indeed. No passwords, no separate browser.
        </CardDescription>
        <CardAction>
          {extension.connected ? <Badge className="bg-success-soft text-success">Connected</Badge> : <Badge variant="secondary">Not connected</Badge>}
        </CardAction>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 text-sm">
        {key ? (
          <div className="grid grid-cols-1 gap-2 rounded-lg border bg-muted/40 p-3">
            <p className="font-medium">Your key (shown only now)</p>
            <div className="flex gap-2">
              <code className="min-w-0 flex-1 truncate rounded bg-background px-2 py-1.5 text-xs" aria-label="Extension key">{key}</code>
              <Button size="sm" variant="outline" onClick={copy}><Copy /> Copy</Button>
            </div>
          </div>
        ) : null}
        <ol className="grid list-decimal gap-1 pl-5 text-muted-foreground">
          <li>In Chrome open <b>chrome://extensions</b>, turn on <b>Developer mode</b>, press <b>Load unpacked</b> and pick the project&apos;s <b>extension</b> folder.</li>
          <li>Press <b>Connect extension</b> below and copy the key.</li>
          <li>Click the extension&apos;s icon, paste the key, press <b>Save and test</b>, then <b>Start</b>.</li>
        </ol>
        {extension.connected && extension.last_seen ? (
          <p className="text-xs text-muted-foreground">Last used {formatDateTime(extension.last_seen)}</p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={connect} disabled={busy}><Puzzle /> {extension.connected ? "New key" : "Connect extension"}</Button>
          {extension.connected ? <Button size="sm" variant="ghost" onClick={disconnect}><Unplug /> Disconnect</Button> : null}
        </div>
      </CardContent>
    </Card>
  );
}
