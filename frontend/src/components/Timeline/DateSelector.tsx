import { ChevronLeft, ChevronRight, Calendar } from "lucide-react";
import { Button } from "@/components/shadcn/button";

interface DateSelectorProps {
  date: string; // YYYY-MM-DD
  onChange: (date: string) => void;
}

function shiftDate(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function DateSelector({ date, onChange }: DateSelectorProps) {
  const isToday = date === todayStr();
  const label = new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="icon" onClick={() => onChange(shiftDate(date, -1))} aria-label="Previous day">
        <ChevronLeft className="h-4 w-4" />
      </Button>

      <div className="relative">
        <div className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
          <Calendar className="h-4 w-4 text-gray-400" />
          {label}
        </div>
        <input
          type="date"
          value={date}
          max={todayStr()}
          onChange={(e) => e.target.value && onChange(e.target.value)}
          className="absolute inset-0 cursor-pointer opacity-0"
          aria-label="Select date"
        />
      </div>

      <Button
        variant="outline"
        size="icon"
        onClick={() => onChange(shiftDate(date, 1))}
        disabled={isToday}
        aria-label="Next day"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>

      {!isToday && (
        <Button variant="secondary" size="sm" onClick={() => onChange(todayStr())}>
          Today
        </Button>
      )}
    </div>
  );
}
