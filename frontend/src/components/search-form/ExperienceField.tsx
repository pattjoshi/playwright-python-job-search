import { Field } from "@/components/ui/Field";
import { InlineCheck } from "@/components/ui/InlineCheck";
import type { Experience } from "@/hooks/useSearchForm";

import styles from "./ExperienceField.module.css";

interface ExperienceFieldProps {
  value: Experience;
  onChange: (value: Experience) => void;
}

/** "1 to 3 years", or Any. */
export function ExperienceField({ value, onChange }: ExperienceFieldProps) {
  return (
    <Field
      label={<span id="exp-label">Experience</span>}
      hint={<InlineCheck checked={value.any} onChange={(any) => onChange({ ...value, any })}>Any</InlineCheck>}
    >
      <div className={styles.range} role="group" aria-labelledby="exp-label">
        <input
          className="input" type="number" min={0} max={50} value={value.min} disabled={value.any}
          aria-label="Experience from (years)" onChange={(e) => onChange({ ...value, min: e.target.value })}
        />
        <span className={styles.unit}>to</span>
        <input
          className="input" type="number" min={0} max={50} value={value.max} disabled={value.any}
          aria-label="Experience to (years)" onChange={(e) => onChange({ ...value, max: e.target.value })}
        />
        <span className={styles.unit}>years</span>
      </div>
    </Field>
  );
}
