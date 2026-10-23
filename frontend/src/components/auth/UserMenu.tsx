"use client";

import { LogOut, Settings } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/providers/AuthProvider";

export function initials(name: string, email: string): string {
  const words = (name || email.split("@")[0]).split(/[\s._-]+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] ?? "?").slice(0, 2)).toUpperCase();
}

/** The round avatar in the top bar: who's signed in, Settings and Sign out. */
export function UserMenu() {
  const { user, signOut } = useAuth();
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full" aria-label="Account menu">
          <span className="grid size-8 place-items-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
            {initials(user.name, user.email)}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-2">
        <div className="px-2 py-1.5">
          <p className="truncate text-sm font-semibold">{user.name || "Your account"}</p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        </div>
        <Separator className="my-1.5" />
        <Button asChild variant="ghost" className="w-full justify-start">
          <Link href="/settings"><Settings /> Settings</Link>
        </Button>
        <Button variant="ghost" className="w-full justify-start" onClick={signOut}>
          <LogOut /> Sign out
        </Button>
      </PopoverContent>
    </Popover>
  );
}
