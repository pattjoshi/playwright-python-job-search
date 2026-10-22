import { Card, CardBody, CardHead } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Segmented } from "@/components/ui/Segmented";
import type { SearchFormApi } from "@/hooks/useSearchForm";
import { HOUR_OPTIONS } from "@/lib/constants";

import { ExperienceField } from "./ExperienceField";
import { KeywordsField } from "./KeywordsField";
import { LocationsField } from "./LocationsField";

/** Step 2: keywords, locations, experience and how recent the posts should be. */
export function LookForCard({ form: api, locationChoices }: { form: SearchFormApi; locationChoices: string[] }) {
  const { form, update, setKeywords, setLocations } = api;
  return (
    <Card>
      <CardBody>
        <CardHead step={2}>What to look for</CardHead>
        <KeywordsField keywords={form.keywords} onChange={setKeywords} />
        <LocationsField choices={locationChoices} locations={form.locations} onChange={setLocations} />
        <ExperienceField value={form.experience} onChange={(experience) => update({ experience })} />
        <Field label={<span id="hours-label">Posted within</span>}>
          <Segmented
            labelledBy="hours-label" value={form.hours} onChange={(hours) => update({ hours })}
            options={HOUR_OPTIONS.map((option) => ({ value: option.hours, label: option.label }))}
          />
        </Field>
      </CardBody>
    </Card>
  );
}
