"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api/endpoints";

const LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#faq", label: "FAQ" },
];

/** Top bar of the home page: shows "Open dashboard" when you're already signed in. */
export function HomeHeader() {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    authApi.status().then((status) => setSignedIn(!!status.user)).catch(() => undefined);
  }, []);
  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid size-8 place-items-center rounded-lg bg-primary font-bold text-primary-foreground">J</span>
          <span className="font-bold">Job Search</span>
        </Link>
        <nav className="hidden gap-5 text-sm text-muted-foreground md:flex" aria-label="Home page">
          {LINKS.map((link) => <a key={link.href} href={link.href} className="hover:text-foreground">{link.label}</a>)}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <Button asChild size="sm"><Link href={signedIn ? "/dashboard" : "/login"}>{signedIn ? "Open dashboard" : "Sign in"}</Link></Button>
        </div>
      </div>
    </header>
  );
}
