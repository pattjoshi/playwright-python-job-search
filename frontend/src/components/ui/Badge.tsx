import styles from "./Badge.module.css";

export type BadgeKind = "new" | "site" | "applied" | "done" | "stopped" | "error";

export function Badge({ kind, children }: { kind: BadgeKind; children: React.ReactNode }) {
  return <span className={`${styles.badge} ${styles[kind]}`}>{children}</span>;
}
