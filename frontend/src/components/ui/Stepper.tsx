import styles from "./Stepper.module.css";

interface StepperProps {
  value: string | number;
  onChange: (value: string) => void;
  min: number;
  max: number;
  label: string;
  disabled?: boolean;
}

/** A number box with − and + buttons. */
export function Stepper({ value, onChange, min, max, label, disabled }: StepperProps) {
  const step = (delta: number) => {
    const next = Math.min(max, Math.max(min, (parseInt(String(value), 10) || 0) + delta));
    onChange(String(next));
  };
  return (
    <span className={styles.stepper}>
      <button type="button" aria-label={`Fewer ${label}`} disabled={disabled} onClick={() => step(-1)}>−</button>
      <input
        type="number" inputMode="numeric" min={min} max={max} value={value} disabled={disabled}
        aria-label={label} onChange={(e) => onChange(e.target.value)}
      />
      <button type="button" aria-label={`More ${label}`} disabled={disabled} onClick={() => step(1)}>+</button>
    </span>
  );
}
