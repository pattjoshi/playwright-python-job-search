import { Minus, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

interface StepperProps {
  value: string | number;
  onChange: (value: string) => void;
  min: number;
  max: number;
  label: string;
  disabled?: boolean;
  className?: string;
}

/** A number box with − and + buttons. */
export function Stepper({ value, onChange, min, max, label, disabled, className }: StepperProps) {
  const step = (delta: number) => onChange(String(Math.min(max, Math.max(min, (parseInt(String(value), 10) || 0) + delta))));
  const button = "grid h-8 w-8 place-items-center bg-muted text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none";
  return (
    <span className={cn("inline-flex items-center overflow-hidden rounded-md border border-input", disabled && "opacity-50", className)}>
      <button type="button" className={button} aria-label={`Fewer ${label}`} disabled={disabled} onClick={() => step(-1)}>
        <Minus className="size-3.5" />
      </button>
      <input
        type="number" inputMode="numeric" min={min} max={max} value={value} disabled={disabled} aria-label={label}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-12 border-x border-input bg-background text-center text-sm outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
      />
      <button type="button" className={button} aria-label={`More ${label}`} disabled={disabled} onClick={() => step(1)}>
        <Plus className="size-3.5" />
      </button>
    </span>
  );
}
