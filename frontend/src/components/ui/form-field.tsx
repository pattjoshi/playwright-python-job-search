interface FormFieldProps {
  label: React.ReactNode;
  hint?: React.ReactNode;
  children: React.ReactNode;
}

/** A form row: label on the left, an optional hint on the right, the control below. */
export function FormField({ label, hint, children }: FormFieldProps) {
  return (
    <div className="grid grid-cols-1 gap-1.5">
      <div className="flex items-baseline justify-between gap-2 text-sm font-medium">
        {label}
        {hint ? <span className="text-xs font-normal text-muted-foreground">{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}
