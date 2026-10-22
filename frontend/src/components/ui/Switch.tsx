import styles from "./Switch.module.css";

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  id?: string;
}

/** An on/off toggle (a styled checkbox, so it works with the keyboard and screen readers). */
export function Switch({ checked, onChange, label, id }: SwitchProps) {
  return (
    <span className={styles.switch}>
      <input id={id} type="checkbox" checked={checked} aria-label={label} onChange={(e) => onChange(e.target.checked)} />
      <span className={styles.track} />
    </span>
  );
}
