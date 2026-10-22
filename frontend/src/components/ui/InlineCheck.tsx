import styles from "./InlineCheck.module.css";

interface InlineCheckProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: React.ReactNode;
}

/** A small checkbox with its label, e.g. "☐ Any" or "☑ Open report when ready". */
export function InlineCheck({ checked, onChange, children }: InlineCheckProps) {
  return (
    <label className={styles.check}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /> {children}
    </label>
  );
}
