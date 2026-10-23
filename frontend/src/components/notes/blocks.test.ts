import { describe, expect, it } from "vitest";

import type { NoteSummary } from "@/lib/types";

import { listNumber, menuMatches, newBlock, nextType, pathTo, shortcut, withDescendants } from "./blocks";

const page = (id: number, parent_id: number | null) => ({ id, parent_id, title: `P${id}` }) as NoteSummary;

describe("note blocks", () => {
  it("turns Markdown shortcuts into blocks", () => {
    expect(shortcut("# ")).toBe("h1");
    expect(shortcut("### ")).toBe("h3");
    expect(shortcut("- ")).toBe("bullet");
    expect(shortcut("1. ")).toBe("numbered");
    expect(shortcut("[] ")).toBe("todo");
    expect(shortcut("---")).toBe("divider");
    expect(shortcut("#hashtag")).toBeNull();
  });

  it("continues lists on Enter and numbers them", () => {
    expect(nextType("bullet")).toBe("bullet");
    expect(nextType("h1")).toBe("paragraph");
    const blocks = [newBlock("numbered"), newBlock("numbered"), newBlock("paragraph"), newBlock("numbered")];
    expect([0, 1, 3].map((i) => listNumber(blocks, i))).toEqual([1, 2, 1]);
  });

  it("filters the / menu", () => {
    expect(menuMatches("head").map((m) => m.type)).toEqual(["h1", "h2", "h3"]);
    expect(menuMatches("todo")[0].type).toBe("todo");
  });

  it("knows a page's branch and its path", () => {
    const pages = [page(1, null), page(2, 1), page(3, 2), page(4, null)];
    expect([...withDescendants(pages, 1)].sort()).toEqual([1, 2, 3]);
    expect(pathTo(pages, 3).map((p) => p.id)).toEqual([1, 2, 3]);
  });
});
