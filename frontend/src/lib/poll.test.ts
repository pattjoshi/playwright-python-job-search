import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HIDDEN_POLL_MS, POLL_MS } from "./constants";
import { pollDelay, waitForNextPoll } from "./poll";

// Tests run in Node: a tiny stand-in for the browser's document and window.
const page = Object.assign(new EventTarget(), { hidden: false });

describe("polling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("document", page);
    vi.stubGlobal("window", globalThis);
    page.hidden = false;
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("checks often while you look, rarely in a background tab", () => {
    expect(pollDelay()).toBe(POLL_MS);
    page.hidden = true;
    expect(pollDelay()).toBe(HIDDEN_POLL_MS);
  });

  it("checks at once when you come back to the tab", async () => {
    page.hidden = true;
    let done = false;
    void waitForNextPoll().then(() => (done = true));
    await vi.advanceTimersByTimeAsync(POLL_MS * 2);
    expect(done).toBe(false);
    page.hidden = false;
    page.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(0);
    expect(done).toBe(true);
  });
});
