"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** For now the app opens on the dashboard (Phase 1 turns this into the home page). */
export default function RootPage() {
  const router = useRouter();
  useEffect(() => router.replace("/dashboard"), [router]);
  return null;
}
