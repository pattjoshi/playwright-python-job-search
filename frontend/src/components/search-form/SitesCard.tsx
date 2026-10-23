import { Card, CardContent } from "@/components/ui/card";
import { StepTitle } from "@/components/ui/step-title";
import { Stepper } from "@/components/ui/stepper";
import { Switch } from "@/components/ui/switch";
import type { SearchFormApi } from "@/hooks/useSearchForm";
import type { SiteConfig } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Step 3: which job sites to search, and how many jobs to show from each. */
export function SitesCard({ form: api, sites }: { form: SearchFormApi; sites: SiteConfig[] }) {
  const { form, update } = api;
  const setSite = (id: string, patch: Partial<{ on: boolean; results: string }>) =>
    update({ sites: { ...form.sites, [id]: { ...form.sites[id], ...patch } } });

  return (
    <Card className="gap-3 py-5">
      <CardContent className="grid grid-cols-1 px-5">
        <StepTitle step={3} aside="Jobs to show">Job sites</StepTitle>
        <div className="mt-2 divide-y">
          {sites.map((site) => {
            const value = form.sites[site.id] ?? { on: false, results: site.results };
            return (
              <div key={site.id} className="flex items-center gap-3 py-2.5">
                <Switch id={`site-${site.id}`} checked={value.on} aria-label={`Search ${site.name}`} onCheckedChange={(on) => setSite(site.id, { on })} />
                <label htmlFor={`site-${site.id}`} className={cn("flex-1 text-sm font-semibold", !value.on && "opacity-50")}>{site.name}</label>
                <Stepper
                  value={value.results} min={1} max={100} disabled={!value.on} label={`${site.name} jobs`}
                  onChange={(results) => setSite(site.id, { results })}
                />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
