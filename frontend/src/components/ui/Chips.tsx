import styles from "./Chips.module.css";

export type ChipKind = "key" | "skill" | "have" | "miss";

interface ChipRowProps {
  label: string;
  items: string[];
  kind: ChipKind;
}

/** "MATCHING  Python  FastAPI" — a label followed by small rounded chips. Hidden when empty. */
export function ChipRow({ label, items, kind }: ChipRowProps) {
  if (!items.length) return null;
  return (
    <div className={styles.chips}>
      <span className={styles.label}>{label}</span>
      {items.map((item) => (
        <span key={item} className={`${styles.chip} ${styles[kind]}`}>{item}</span>
      ))}
    </div>
  );
}

export function ChipLabel({ children }: { children: React.ReactNode }) {
  return <span className={styles.label}>{children}</span>;
}

export function Chip({ kind, children }: { kind: ChipKind; children: React.ReactNode }) {
  return <span className={`${styles.chip} ${styles[kind]}`}>{children}</span>;
}

export function Chips({ children }: { children: React.ReactNode }) {
  return <div className={styles.chips}>{children}</div>;
}
