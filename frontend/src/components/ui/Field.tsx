import type { ReactNode } from "react";

import styles from "./Field.module.css";

interface FieldProps {
  label: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
}

/** A form row: label on the left, an optional hint on the right, the control below. */
export function Field({ label, hint, children }: FieldProps) {
  return (
    <div className={styles.field}>
      <div className={styles.label}>
        {label}
        {hint ? <span className={styles.hint}>{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}
