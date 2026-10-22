import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";

import styles from "./Button.module.css";

type Variant = "primary" | "danger" | "secondary" | "link" | "icon";

const classes = (variant: Variant, block?: boolean, extra?: string) =>
  [variant === "link" || variant === "icon" ? "" : styles.btn, styles[variant], block ? styles.block : "", extra ?? ""]
    .filter(Boolean)
    .join(" ");

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  block?: boolean;
}

export function Button({ variant = "secondary", block, className, type = "button", ...props }: ButtonProps) {
  return <button type={type} className={classes(variant, block, className)} {...props} />;
}

interface LinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: Variant;
  /** Opens in a new tab (for job pages and reports). */
  external?: boolean;
}

export function LinkButton({ variant = "secondary", external, className, ...props }: LinkButtonProps) {
  const target = external ? { target: "_blank", rel: "noopener noreferrer" } : {};
  return <a className={classes(variant, false, className)} {...target} {...props} />;
}
