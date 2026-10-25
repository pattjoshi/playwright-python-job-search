/** Waits between status checks: short while you're looking, long while the tab is hidden, cut short when you return. */

import { HIDDEN_POLL_MS, POLL_MS } from "@/lib/constants";

export function pollDelay(): number {
  return typeof document !== "undefined" && document.hidden ? HIDDEN_POLL_MS : POLL_MS;
}

export function waitForNextPoll(): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
      resolve();
    };
    const onVisible = () => !document.hidden && done();
    const timer = window.setTimeout(done, pollDelay());
    document.addEventListener("visibilitychange", onVisible);
  });
}
