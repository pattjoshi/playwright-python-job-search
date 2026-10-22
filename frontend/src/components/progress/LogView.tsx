"use client";

import { useLayoutEffect, useRef } from "react";


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
    <details className="mt-3">
      <summary className="cursor-pointer text-xs text-muted-foreground">Show log</summary>
      <pre
        ref={pre} onScroll={onScroll}
        className="mt-2 max-h-56 overflow-auto rounded-md border bg-muted/40 p-2.5 font-mono text-xs whitespace-pre-wrap"
      >
        {text}
      </pre>
    </details>
  );
}
