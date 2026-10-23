"use client";

import { useRef, useState } from "react";

import { FormField } from "@/components/ui/form-field";
import { TagInput } from "@/components/ui/tag-input";
import { REMOTE } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface LocationsFieldProps {
  choices: string[];
  locations: string[];
  onChange: (locations: string[]) => void;
}

const GROUP = "px-2.5 pt-1.5 pb-0.5 text-[11px] font-bold tracking-wider text-muted-foreground uppercase";

interface Option {
  value: string;
  custom?: boolean;
}

/** Multi-select of Indian tech cities and Remote, with type-to-filter and free-text entries. */
export function LocationsField({ choices, locations, onChange }: LocationsFieldProps) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const input = useRef<HTMLInputElement>(null);

  const query = text.trim().toLowerCase();
  const exact = choices.some((c) => c.toLowerCase() === query) || locations.some((c) => c.toLowerCase() === query);
  // Known cities first, so typing "hyd" + Enter picks Hyderabad; "Add …" is the fallback.
  const options: Option[] = [
    ...choices.filter((c) => c.toLowerCase().includes(query)).map((value) => ({ value })),
    ...(query && !exact ? [{ value: text.trim(), custom: true }] : []),
  ];
  const highlighted = Math.min(active, options.length - 1);

  const toggle = (value: string) => {
    onChange(locations.includes(value) ? locations.filter((l) => l !== value) : [...locations, value]);
    setText("");
  };
  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive(Math.min(highlighted + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive(Math.max(highlighted - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const option = options[Math.max(highlighted, 0)];
      if (option) toggle(option.value);
    } else if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Backspace" && !text && locations.length) {
      onChange(locations.slice(0, -1));
    }
  };

  return (
    <FormField label={<label htmlFor="location-input" id="location-label">Locations</label>} hint="Empty = from your resume">
      <div className="relative">
        <TagInput
          tags={locations} onRemove={(l) => onChange(locations.filter((x) => x !== l))}
          onClick={() => { input.current?.focus(); setOpen(true); }}
        >
          <input
            ref={input} id="location-input" role="combobox" aria-expanded={open} aria-controls="location-list"
            aria-autocomplete="list" aria-activedescendant={open && highlighted >= 0 ? `loc-opt-${highlighted}` : undefined}
            placeholder="Search cities or Remote" autoComplete="off" value={text} onKeyDown={onKeyDown}
            onChange={(e) => { setText(e.target.value); setOpen(true); setActive(0); }}
            onFocus={() => { setOpen(true); setActive(-1); }} onBlur={() => setOpen(false)}
          />
        </TagInput>
        {open ? (
          <ul
            className="absolute inset-x-0 top-[calc(100%+4px)] z-30 m-0 max-h-64 list-none overflow-auto rounded-lg border bg-popover p-1 text-popover-foreground shadow-lg"
            id="location-list" role="listbox" aria-multiselectable="true" aria-labelledby="location-label">
            {!query ? <li className={GROUP} role="presentation">Popular in India</li> : null}
            {options.map((option, index) => {
              const selected = locations.includes(option.value);
              return (
                <li
                  key={`${option.custom ? "add:" : ""}${option.value}`} id={`loc-opt-${index}`} role="option"
                  aria-selected={selected}
                  className={cn("flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-sm", index === highlighted && "bg-accent")}
                  onMouseDown={(e) => { e.preventDefault(); toggle(option.value); }}
                >
                  <span className={cn("grid size-4 shrink-0 place-items-center rounded border-[1.5px] border-input text-[11px] text-primary-foreground",
                    selected && "border-primary bg-primary")}
                  >
                    {selected ? "✓" : ""}
                  </span>
                  {option.custom ? `Add “${option.value}”` : option.value}
                  {option.value === REMOTE ? <span className="ml-auto text-xs text-muted-foreground">Work from home</span> : null}
                </li>
              );
            })}
            {!options.length ? <li className={GROUP}>No matches</li> : null}
          </ul>
        ) : null}
      </div>
    </FormField>
  );
}
