/** Where to go after signing in: the ?next= page, only if it's a page of this app (no open redirects). */
export function nextUrl(search: string = typeof window === "undefined" ? "" : window.location.search): string {
  const next = new URLSearchParams(search).get("next") ?? "";
  return next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/dashboard";
}
