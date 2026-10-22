/** Rough "how long will this take" shown above the Start button. */

import { REMOTE } from "@/lib/constants";

export interface EstimateInput {
  sites: string[];
  keywords: number;
  locations: string[];
  maxPages: number;
  top: number;
  parallel: boolean;
}

export interface Estimate {
  text: string;
  tip: boolean;
}

export function estimateSearch({ sites, keywords, locations, maxPages, top, parallel }: EstimateInput): Estimate {
  if (!sites.length) return { text: "Pick at least one job site", tip: false };
  const words = keywords || 3;
  const remote = locations.includes(REMOTE) ? 1 : 0;
  const cities = Math.max(locations.length - remote, locations.length ? 0 : 1);
  const pages = maxPages || 3;
  const scored = top || 40;
  // Naukri searches all cities in one request; the others search city by city.
  const perSite = sites.map((site) => words * (site === "naukri" ? Math.min(cities, 1) + remote : cities + remote));
  const searches = perSite.reduce((a, b) => a + b, 0);
  const siteMinutes = perSite.map((n) => (n * pages * 6 + scored * 3) / 60);
  const total = parallel ? Math.max(0, ...siteMinutes) : siteMinutes.reduce((a, b) => a + b, 0);
  const minutes = Math.max(1, Math.round(total));
  const together = parallel && sites.length > 1 ? " (sites run at the same time)" : "";
  return {
    text: `${searches} searches across ${sites.length} site${sites.length > 1 ? "s" : ""} · about ${minutes} min${together}`,
    tip: Math.max(0, ...perSite) > 12,
  };
}
