import type { ContextSwitchingHour } from "@/api";
import { CONTEXT_SWITCH_HIGH_THRESHOLD, CONTEXT_SWITCH_MODERATE_THRESHOLD } from "./thresholds";

interface ContextSwitchingStripProps {
  hours: ContextSwitchingHour[];
  startHour: number;
  endHour: number;
}

function toneFor(count: number): string {
  if (count > CONTEXT_SWITCH_HIGH_THRESHOLD) return "bg-error-400";
  if (count > CONTEXT_SWITCH_MODERATE_THRESHOLD) return "bg-warning-400";
  return "bg-success-400";
}

function hourLabel(hour: number): string {
  const h = hour % 12 === 0 ? 12 : hour % 12;
  return `${h}${hour < 12 ? "am" : "pm"}`;
}

export default function ContextSwitchingStrip({ hours, startHour, endHour }: ContextSwitchingStripProps) {
  const byHour = new Map(hours.map((h) => [h.hour, h.switch_count]));
  const range = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);

  return (
    <div>
      <p className="mb-1.5 text-theme-xs font-medium text-gray-500 dark:text-gray-400">
        Context switching by hour
      </p>
      <div className="flex gap-1">
        {range.map((hour) => {
          const count = byHour.get(hour) ?? 0;
          return (
            <div
              key={hour}
              className={`h-3 flex-1 rounded-sm transition-colors ${count > 0 ? toneFor(count) : "bg-gray-100 dark:bg-white/5"}`}
              title={`${hourLabel(hour)} — ${count} switch${count === 1 ? "" : "es"}`}
            />
          );
        })}
      </div>
      <div className="mt-1 flex gap-1">
        {range.map((hour) => (
          <div key={hour} className="flex-1 text-center text-[10px] text-gray-400 dark:text-gray-500">
            {hour % 2 === 0 ? hourLabel(hour) : ""}
          </div>
        ))}
      </div>
    </div>
  );
}
