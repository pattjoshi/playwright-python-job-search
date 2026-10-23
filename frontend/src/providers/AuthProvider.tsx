"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { ShellSkeleton } from "@/components/layout/ShellSkeleton";
import { authApi } from "@/lib/api/endpoints";
import { redirectToSignIn } from "@/lib/api/client";
import type { AuthUser } from "@/lib/types";

interface AuthContextValue {
  user: AuthUser;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Guards the app pages: shows them only to a signed-in user, otherwise sends you to the sign-in page. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    authApi.status()
      .then((status) => (status.user ? setUser(status.user) : redirectToSignIn()))
      .catch(() => redirectToSignIn());
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      window.location.replace("/login");
    }
  }, []);

  if (!user) return <ShellSkeleton />;
  return <AuthContext.Provider value={{ user, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
