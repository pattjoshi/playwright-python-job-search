"use client";

import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface PasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: "current-password" | "new-password" | "off";
  hint?: string;
}

/** A password box with a show/hide button. */
export function PasswordField({ id, label, value, onChange, autoComplete, hint }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="grid grid-cols-1 gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id} type={visible ? "text" : "password"} value={value} autoComplete={autoComplete} required className="pr-10"
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button" onClick={() => setVisible((v) => !v)} aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          className="absolute inset-y-0 right-0 grid w-10 place-items-center text-muted-foreground hover:text-foreground"
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
