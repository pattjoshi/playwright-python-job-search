"use client";

import { useLayoutEffect, useRef } from "react";

import styles from "./LogView.module.css";

/** The search log, collapsed by default. Keeps following new lines while scrolled to the bottom. */
export function LogView({ lines }: { lines: string[] }) {
  const pre = useRef<HTMLPreElement>(null);
  const following = useRef(true);
  const text = lines.join("\n");

  useLayoutEffect(() => {
    const node = pre.current;
    if (node && following.current) node.scrollTop = node.scrollHeight;
  }, [text]);

  const onScroll = () => {
    const node = pre.current;
    if (node) following.current = node.scrollTop + node.clientHeight >= node.scrollHeight - 4;
  };

  return (
    <details className={styles.log}>
      <summary>Show log</summary>
      <pre ref={pre} onScroll={onScroll}>{text}</pre>
    </details>
  );
}
