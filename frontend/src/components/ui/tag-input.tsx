import { X } from "lucide-react";

interface TagInputProps {
  tags: string[];
  onRemove: (tag: string) => void;
  onClick?: () => void;
  children: React.ReactNode; // the text input
}

/** A text box that shows its values as removable tags in front of the input. */
export function TagInput({ tags, onRemove, onClick, children }: TagInputProps) {
  return (
    <div
      onClick={onClick}
      className="flex min-h-9 w-full cursor-text flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1.5 shadow-xs transition-[color,box-shadow] focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50 dark:bg-input/30 [&_input]:min-w-24 [&_input]:flex-1 [&_input]:bg-transparent [&_input]:px-1 [&_input]:text-sm [&_input]:outline-none [&_input]:placeholder:text-muted-foreground"
    >
      {tags.map((tag) => (
        <span key={tag} className="inline-flex items-center gap-1 rounded-md bg-accent py-0.5 pr-1 pl-2 text-[13px] font-semibold text-accent-foreground">
          {tag}
          <button
            type="button" aria-label={`Remove ${tag}`} className="rounded p-0.5 opacity-70 hover:bg-foreground/10 hover:opacity-100"
            onClick={(e) => { e.stopPropagation(); onRemove(tag); }} // removing shouldn't open the city list
          >
            <X className="size-3.5" />
          </button>
        </span>
      ))}
      {children}
    </div>
  );
}
