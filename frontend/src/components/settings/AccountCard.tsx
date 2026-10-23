"use client";

import { useState } from "react";
import { toast } from "sonner";

import { initials } from "@/components/auth/UserMenu";
import { PasswordField } from "@/components/auth/PasswordField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/providers/AuthProvider";

/** Who is signed in, change password, and sign out of every browser. */
export function AccountCard() {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<string | null>(null);

  const change = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await authApi.changePassword(current, next);
      setCurrent("");
      setNext("");
      toast.success("Password changed. Other browsers were signed out.");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const signOutEverywhere = async () => {
    await authApi.logoutEverywhere().catch(() => undefined);
    window.location.replace("/login");
  };

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>Account</CardTitle>
        <CardDescription>Your sign-in for this app.</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="flex items-center gap-3">
          <span className="grid size-12 shrink-0 place-items-center rounded-full bg-primary font-bold text-primary-foreground">
            {initials(user.name, user.email)}
          </span>
          <div className="min-w-0">
            <p className="truncate font-semibold">{user.name || "Your account"}</p>
            <p className="truncate text-sm text-muted-foreground">{user.email}</p>
            <Badge variant="secondary" className="mt-1 capitalize">{user.role}</Badge>
          </div>
        </div>
        <form className="grid grid-cols-1 gap-3" onSubmit={change}>
          <PasswordField id="current-password" label="Current password" value={current} onChange={setCurrent} autoComplete="current-password" />
          <PasswordField id="new-password" label="New password" value={next} onChange={setNext} autoComplete="new-password" hint="At least 8 characters." />
          {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
          <Button type="submit" variant="outline" className="w-fit" disabled={!current || !next}>Change password</Button>
        </form>
        <div className="lg:col-span-2">
          <Separator className="mb-4" />
          <Button variant="ghost" className="text-destructive hover:text-destructive" onClick={signOutEverywhere}>
            Sign out of every browser
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
