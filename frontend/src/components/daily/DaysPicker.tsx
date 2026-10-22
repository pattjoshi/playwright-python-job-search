import { Button } from "@/components/ui/Button";
import { ALL_DAYS, DAY_LABELS, WEEKDAYS } from "@/lib/constants";

import styles from "./DaysPicker.module.css";

interface DaysPickerProps {
  days: string[];
  onChange: (days: string[]) => void;
  labelledBy: string;
}

export function DaysPicker({ days, onChange, labelledBy }: DaysPickerProps) {
  const toggle = (day: string) => onChange(days.includes(day) ? days.filter((d) => d !== day) : [...days, day]);
  return (
    <>
      <div className={styles.days} role="group" aria-labelledby={labelledBy}>
        {ALL_DAYS.map((day) => (
          <button key={day} type="button" aria-pressed={days.includes(day)} aria-label={DAY_LABELS[day]} onClick={() => toggle(day)}>
            {DAY_LABELS[day].slice(0, 2)}
          </button>
        ))}
      </div>
      <div className={styles.quick}>
        <Button variant="link" onClick={() => onChange(ALL_DAYS)}>Every day</Button>
        <Button variant="link" onClick={() => onChange(WEEKDAYS)}>Weekdays</Button>
      </div>
    </>
  );
}
