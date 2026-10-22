import type { SiteConfig, SiteProgress } from "@/lib/types";
import { cn } from "@/lib/utils";

function label(info: SiteProgress): string {
  switch (info.status) {
    case "waiting": return "waiting";
    case "running": return info.found ? `${info.found} found…` : "searching…";
    case "done": return `${info.found} found ✓`;
    case "failed": return "couldn't load";
    default: return info.status;
  }
}

/** One chip per site: "LinkedIn 42 found ✓". */
export function SiteStatus({ sites, progress }: { sites: SiteConfig[]; progress: Record<string, SiteProgress> }) {
  return (
    <div className="mt-3.5 flex flex-wrap gap-2">
      {sites.filter((site) => progress[site.id]).map((site) => {
        const info = progress[site.id];
        return (
          <span key={site.id} className={cn("inline-flex items-center gap-1.5 rounded-md border bg-muted/40 px-2.5 py-1 text-sm", info.status === "running" && "border-primary")}>
            <b>{site.name}</b>
            <span className={cn("text-muted-foreground", info.status === "done" && "text-success", info.status === "failed" && "text-destructive")}>
              {label(info)}
            </span>
          </span>
        );
      })}
    </div>
  );
}
