import type { ReactNode } from "react";

import styles from "./TagControl.module.css";

interface TagControlProps {
  tags: string[];
  onRemove: (tag: string) => void;
  onClick?: () => void;
  children: ReactNode; // the text input
}

/** A text box that shows its values as removable tags in front of the input. */
export function TagControl({ tags, onRemove, onClick, children }: TagControlProps) {
  return (
    <div className={styles.control} onClick={onClick}>
      {tags.map((tag) => (
        <span key={tag} className={styles.tag}>
          {tag}
          <button
            type="button" aria-label={`Remove ${tag}`}
            onClick={(e) => { e.stopPropagation(); onRemove(tag); }} // removing shouldn't open the city list
          >
            ×
          </button>
        </span>
      ))}
      {children}
    </div>
  );
}
