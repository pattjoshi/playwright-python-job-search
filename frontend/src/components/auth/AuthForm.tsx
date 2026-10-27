"use client";

import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { authApi } from "@/lib/api/endpoints";

import { PasswordField } from "./PasswordField";

/** Sign in, or (first run) create the owner account. Calls onDone after the session cookie is set. */
export function AuthForm({ mode, onDone, needsCode = false }: { mode: "setup" | "signin"; onDone: () => void; needsCode?: boolean }) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const setup = mode === "setup";

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (setup && password !== confirm) return setError("The two passwords don't match.");
    setBusy(true);
    try {
      await (setup ? authApi.setup({ name, email, password, ...(needsCode ? { setup_code: code } : {}) }) : authApi.login({ email, password }));
      onDone();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <form className="grid grid-cols-1 gap-4" onSubmit={submit}>
      {setup ? (
        <div className="grid grid-cols-1 gap-1.5">
          <Label htmlFor="name">Your name</Label>
          <Input id="name" value={name} autoComplete="name" onChange={(e) => setName(e.target.value)} />
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" value={email} autoComplete="email" required onChange={(e) => setEmail(e.target.value)} />
      </div>
      <PasswordField
        id="password" label="Password" value={password} onChange={setPassword}
        autoComplete={setup ? "new-password" : "current-password"} hint={setup ? "At least 8 characters." : undefined}
      />
      {setup ? (
        <PasswordField id="confirm" label="Confirm password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
      ) : null}
      {setup && needsCode ? (
        <PasswordField
          id="setup-code" label="Setup code" value={code} onChange={setCode} autoComplete="off"
          hint="The SETUP_CODE you set when deploying: only you can create the account."
        />
      ) : null}
      {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
      <Button type="submit" size="lg" disabled={busy}>
        {busy ? <Spinner aria-hidden="true" /> : null}
        {setup ? "Create account" : "Sign in"}
      </Button>
    </form>
  );
}
