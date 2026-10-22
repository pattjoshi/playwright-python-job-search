import { Card, CardBody, CardHead } from "@/components/ui/Card";
import { Stepper } from "@/components/ui/Stepper";
import { Switch } from "@/components/ui/Switch";
import type { SearchFormApi } from "@/hooks/useSearchForm";
import type { SiteConfig } from "@/lib/types";

import styles from "./SitesCard.module.css";

/** Step 3: which job sites to search, and how many jobs to show from each. */
export function SitesCard({ form: api, sites }: { form: SearchFormApi; sites: SiteConfig[] }) {
  const { form, update } = api;
  const setSite = (id: string, patch: Partial<{ on: boolean; results: string }>) =>
    update({ sites: { ...form.sites, [id]: { ...form.sites[id], ...patch } } });

  return (
    <Card>
      <CardBody>
        <CardHead step={3} aside="Jobs to show">Job sites</CardHead>
        {sites.map((site) => {
          const value = form.sites[site.id] ?? { on: false, results: site.results };
          return (
            <div key={site.id} className={[styles.row, value.on ? "" : styles.off].join(" ")}>
              <Switch id={`site-${site.id}`} checked={value.on} label={`Search ${site.name}`} onChange={(on) => setSite(site.id, { on })} />
              <label className={styles.name} htmlFor={`site-${site.id}`}>{site.name}</label>
              <Stepper
                value={value.results} min={1} max={100} disabled={!value.on} label={`${site.name} jobs`}
                onChange={(results) => setSite(site.id, { results })}
              />
            </div>
          );
        })}
      </CardBody>
    </Card>
  );
}
