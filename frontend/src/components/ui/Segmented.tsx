import styles from "./Segmented.module.css";

interface SegmentedProps<T extends string | number> {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  labelledBy: string;
}

/** A row of buttons where exactly one is selected (like "12 hours | 24 hours | 3 days"). */
export function Segmented<T extends string | number>({ options, value, onChange, labelledBy }: SegmentedProps<T>) {
  return (
    <div className={styles.segmented} role="group" aria-labelledby={labelledBy}>
      {options.map((option) => (
        <button key={option.value} type="button" aria-pressed={option.value === value} onClick={() => onChange(option.value)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}
