"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

/** Light / dark / system theme, stored in the browser and applied as the `dark` class on <html>. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {children}
    </NextThemesProvider>
  );
}
