"use client";

import { useEffect, useRef } from "react";

import { Button } from "./Button";
import styles from "./Sheet.module.css";

interface SheetProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

/** A panel that slides in from the right (a native <dialog>, so Esc and focus handling come for free). */
export function Sheet({ open, title, onClose, children }: SheetProps) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) node.showModal();
    if (!open && node.open) node.close();
  }, [open]);

  return (
    <dialog
      ref={dialog} className={styles.sheet} aria-labelledby="sheet-title" onClose={onClose}
      onClick={(e) => e.target === dialog.current && onClose()}
    >
      <div className={styles.inner}>
        <div className={styles.head}>
          <h2 id="sheet-title">{title}</h2>
          <Button variant="icon" aria-label="Close" onClick={onClose}>×</Button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
