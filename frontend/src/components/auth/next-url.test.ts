import { describe, expect, it } from "vitest";

import { nextUrl } from "./next-url";

describe("nextUrl", () => {
  it("returns to the page you came from", () => {
    expect(nextUrl("?next=%2Fsearch")).toBe("/search");
  });

  it("never leaves the app or loops back to sign-in", () => {
    for (const bad of ["?next=https%3A%2F%2Fevil.example", "?next=%2F%2Fevil.example", "?next=%2Flogin", ""]) {
      expect(nextUrl(bad)).toBe("/dashboard");
    }
  });
});
