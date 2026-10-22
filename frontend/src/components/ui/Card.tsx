import type { HTMLAttributes, ReactNode } from "react";

import styles from "./Card.module.css";

export function Card({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={[styles.card, className].filter(Boolean).join(" ")} {...props} />;
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={[styles.body, className].filter(Boolean).join(" ")} {...props} />;
}

interface CardHeadProps {
  step: number;
  done?: boolean;
  aside?: ReactNode;
  children: ReactNode;
}

/** "1  Resume" style heading with a numbered step that turns into a check mark when done. */
export function CardHead({ step, done, aside, children }: CardHeadProps) {
  return (
    <h2 className={styles.head}>
      <span className={[styles.step, done ? styles.done : ""].join(" ")}>{done ? "✓" : step}</span>
      {children}
      {aside ? <span className={styles.aside}>{aside}</span> : null}
    </h2>
  );
}
