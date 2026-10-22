import { Checkbox } from "@/components/ui/checkbox";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import type { Experience } from "@/hooks/useSearchForm";

interface ExperienceFieldProps {
  value: Experience;
  onChange: (value: Experience) => void;
}

/** "1 to 3 years", or Any. */
export function ExperienceField({ value, onChange }: ExperienceFieldProps) {
  return (
    <FormField
      label={<span id="exp-label">Experience</span>}
      hint={
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-sm text-muted-foreground">
          <Checkbox checked={value.any} onCheckedChange={(checked) => onChange({ ...value, any: checked === true })} aria-label="Any experience" />
          Any
        </label>
      }
    >
      <div className="flex items-center gap-2 text-sm text-muted-foreground" role="group" aria-labelledby="exp-label">
        <Input
          type="number" min={0} max={50} value={value.min} disabled={value.any} className="w-20 text-center"
          aria-label="Experience from (years)" onChange={(e) => onChange({ ...value, min: e.target.value })}
        />
        to
        <Input
          type="number" min={0} max={50} value={value.max} disabled={value.any} className="w-20 text-center"
          aria-label="Experience to (years)" onChange={(e) => onChange({ ...value, max: e.target.value })}
        />
        years
      </div>
    </FormField>
  );
}
