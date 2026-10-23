import type { Metadata } from "next";

import { LoginPage } from "@/components/auth/LoginPage";

export const metadata: Metadata = { title: "Sign in" };

export default function Page() {
  return <LoginPage />;
}
