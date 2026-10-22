import { Card, CardContent } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { StepTitle } from "@/components/ui/step-title";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { SearchFormApi } from "@/hooks/useSearchForm";
import { HOUR_OPTIONS } from "@/lib/constants";

import { ExperienceField } from "./ExperienceField";
import { KeywordsField } from "./KeywordsField";
import { LocationsField } from "./LocationsField";

/** Step 2: keywords, locations, experience and how recent the posts should be. */
export function LookForCard({ form: api, locationChoices }: { form: SearchFormApi; locationChoices: string[] }) {
  const { form, update, setKeywords, setLocations } = api;
  return (
    <Card className="gap-4 py-5">
      <CardContent className="grid grid-cols-1 gap-4 px-5">
        <StepTitle step={2}>What to look for</StepTitle>
        <KeywordsField keywords={form.keywords} onChange={setKeywords} />
        <LocationsField choices={locationChoices} locations={form.locations} onChange={setLocations} />
        <ExperienceField value={form.experience} onChange={(experience) => update({ experience })} />
        <FormField label={<span id="hours-label">Posted within</span>}>
          <ToggleGroup
            type="single" variant="outline" value={String(form.hours)} aria-labelledby="hours-label" className="w-full"
            onValueChange={(value) => value && update({ hours: Number(value) })}
          >
            {HOUR_OPTIONS.map((option) => (
              <ToggleGroupItem key={option.hours} value={String(option.hours)} className="flex-1 text-xs">{option.label}</ToggleGroupItem>
            ))}
          </ToggleGroup>
        </FormField>
      </CardContent>
    </Card>
  );
}
