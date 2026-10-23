import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface TextFieldProps {
  id: string;
  label: string;
  value: string | undefined;
  onChange: (value: string) => void;
  type?: "text" | "url" | "date";
  required?: boolean;
  placeholder?: string;
  className?: string;
}

export function TextField({ id, label, value, onChange, type = "text", required, placeholder, className }: TextFieldProps) {
  return (
    <div className={cn("grid grid-cols-1 gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium">{label}{required ? <span className="text-destructive"> *</span> : null}</label>
      <Input id={id} type={type} value={value ?? ""} required={required} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
