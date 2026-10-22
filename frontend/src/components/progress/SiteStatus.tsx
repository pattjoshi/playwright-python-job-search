import type { SiteConfig, SiteProgress } from "@/lib/types";

import styles from "./SiteStatus.module.css";

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
  const shown = sites.filter((site) => progress[site.id]);
  return (
    <div className={styles.status}>
      {shown.map((site) => {
        const info = progress[site.id];
        return (
          <span key={site.id} className={`${styles.chip} ${styles[info.status] ?? ""}`}>
            <b>{site.name}</b>
            <span className={styles.state}>{label(info)}</span>
          </span>
        );
      })}
    </div>
  );
}
