import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { ALL_DAYS, DAY_LABELS, WEEKDAYS } from "@/lib/constants";

interface DaysPickerProps {
  days: string[];
  onChange: (days: string[]) => void;
  labelledBy: string;
}

export function DaysPicker({ days, onChange, labelledBy }: DaysPickerProps) {
  return (
    <div className="grid grid-cols-1 gap-1.5">
      <ToggleGroup type="multiple" variant="outline" value={days} onValueChange={onChange} aria-labelledby={labelledBy} className="w-full">
        {ALL_DAYS.map((day) => (
          <ToggleGroupItem
            key={day} value={day} aria-label={DAY_LABELS[day]}
            className="flex-1 px-0 text-xs data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
          >
            {DAY_LABELS[day].slice(0, 2)}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <div className="flex gap-3">
        <Button variant="link" size="xs" className="h-auto p-0" onClick={() => onChange(ALL_DAYS)}>Every day</Button>
        <Button variant="link" size="xs" className="h-auto p-0" onClick={() => onChange(WEEKDAYS)}>Weekdays</Button>
      </div>
    </div>
  );
}
