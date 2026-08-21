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
              className={`h-3 flex-1 rounded-sm ${count > 0 ? toneFor(count) : "bg-gray-100 dark:bg-white/5"}`}
              title={`${hour}:00 — ${count} switches`}
            />
          );
        })}
      </div>
    </div>
  );
}
