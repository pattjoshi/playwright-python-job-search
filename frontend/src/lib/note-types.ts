// Notes shapes from /api/notes (re-exported by types.ts).

export type BlockType = "paragraph" | "h1" | "h2" | "h3" | "todo" | "bullet" | "numbered" | "quote" | "code" | "divider";

export interface Block {
  id: string;
  type: BlockType;
  text: string;
  checked: boolean;
}

/** A page in the sidebar tree (no blocks). */
export interface NoteSummary {
  id: number;
  parent_id: number | null;
  title: string;
  icon: string;
  position: number;
  updated_at: string;
}

export interface NotePage extends NoteSummary {
  content: Block[];
  created_at: string;
}
