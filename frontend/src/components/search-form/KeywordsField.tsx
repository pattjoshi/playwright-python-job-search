"use client";

import { useRef, useState } from "react";

import { FormField } from "@/components/ui/form-field";
import { TagInput } from "@/components/ui/tag-input";

interface KeywordsFieldProps {
  keywords: string[];
  onChange: (keywords: string[]) => void;
}

/** Search phrases as tags: Enter or comma adds, × or Backspace removes. */
export function KeywordsField({ keywords, onChange }: KeywordsFieldProps) {
  const [text, setText] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const commit = () => {
    if (!text.trim()) return;
    onChange([...keywords, ...text.split(",")]);
    setText("");
  };
  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !text && keywords.length) {
      onChange(keywords.slice(0, -1));
    }
  };

  return (
    <FormField label={<label htmlFor="keyword-input">Keywords</label>} hint="From your resume · Enter to add">
      <TagInput tags={keywords} onClick={() => input.current?.focus()} onRemove={(keyword) => onChange(keywords.filter((k) => k !== keyword))}>
        <input
          ref={input} id="keyword-input" placeholder="e.g. Python Developer" autoComplete="off"
          value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown} onBlur={commit}
        />
      </TagInput>
    </FormField>
  );
}
