"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const THEMES = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

const subscribe = () => () => {};

export function AppearanceCard() {
  const { theme, setTheme } = useTheme();
  // The saved theme is only known in the browser; show nothing selected until then.
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>“System” follows your computer&apos;s light or dark setting.</CardDescription>
      </CardHeader>
      <CardContent>
        <ToggleGroup
          type="single" variant="outline" value={mounted ? theme : undefined} aria-label="Theme"
          onValueChange={(value) => value && setTheme(value)}
        >
          {THEMES.map(({ value, label, icon: Icon }) => (
            <ToggleGroupItem key={value} value={value} className="px-4">
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </CardContent>
    </Card>
  );
}
