import type { Block, BlockType, NoteSummary } from "@/lib/types";

/** The "/" menu, in the order it shows. */
export const BLOCK_MENU: { type: BlockType; label: string; hint: string }[] = [
  { type: "paragraph", label: "Text", hint: "Plain text" },
  { type: "h1", label: "Heading 1", hint: "# " },
  { type: "h2", label: "Heading 2", hint: "## " },
  { type: "h3", label: "Heading 3", hint: "### " },
  { type: "todo", label: "To-do", hint: "[] " },
  { type: "bullet", label: "Bulleted list", hint: "- " },
  { type: "numbered", label: "Numbered list", hint: "1. " },
  { type: "quote", label: "Quote", hint: "> " },
  { type: "code", label: "Code", hint: "```" },
  { type: "divider", label: "Divider", hint: "---" },
];

const SHORTCUTS: [RegExp, BlockType][] = [
  [/^### $/, "h3"], [/^## $/, "h2"], [/^# $/, "h1"], [/^[-*] $/, "bullet"], [/^1[.)] $/, "numbered"],
  [/^\[ ?\] $/, "todo"], [/^> $/, "quote"], [/^```$/, "code"], [/^---$/, "divider"],
];

export function newBlock(type: BlockType = "paragraph", text = ""): Block {
  return { id: Math.random().toString(36).slice(2, 10), type, text, checked: false };
}

/** Markdown typed at the start of a plain block turns it into that block ("# " → heading). */
export function shortcut(text: string): BlockType | null {
  return SHORTCUTS.find(([pattern]) => pattern.test(text))?.[1] ?? null;
}

/** The block Enter creates: lists and to-dos continue, everything else goes back to text. */
export function nextType(type: BlockType): BlockType {
  return type === "bullet" || type === "numbered" || type === "todo" ? type : "paragraph";
}

/** 1, 2, 3… for consecutive numbered blocks. */
export function listNumber(blocks: Block[], index: number): number {
  let n = 1;
  for (let i = index - 1; i >= 0 && blocks[i].type === "numbered"; i--) n += 1;
  return n;
}

/** "/hea" → the menu items matching "hea". */
export function menuMatches(query: string) {
  const q = query.toLowerCase();
  return BLOCK_MENU.filter((item) => item.label.toLowerCase().includes(q) || item.type.includes(q));
}

/** The ids of a page and every page inside it (they can't become its new parent). */
export function withDescendants(pages: NoteSummary[], id: number): Set<number> {
  const found = new Set([id]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const page of pages) {
      if (page.parent_id !== null && found.has(page.parent_id) && !found.has(page.id)) {
        found.add(page.id);
        grew = true;
      }
    }
  }
  return found;
}

/** Breadcrumbs: the page's parents from the top. */
export function pathTo(pages: NoteSummary[], id: number): NoteSummary[] {
  const byId = new Map(pages.map((page) => [page.id, page]));
  const path: NoteSummary[] = [];
  for (let page = byId.get(id); page; page = page.parent_id === null ? undefined : byId.get(page.parent_id)) {
    path.unshift(page);
  }
  return path;
}
