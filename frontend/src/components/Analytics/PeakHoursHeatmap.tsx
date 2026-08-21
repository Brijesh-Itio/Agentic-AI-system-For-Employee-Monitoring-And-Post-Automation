import type { HeatmapCell } from "@/api";

interface PeakHoursHeatmapProps {
  cells: HeatmapCell[];
}

const START_HOUR = 8;
const END_HOUR = 20;
const HOURS = Array.from({ length: END_HOUR - START_HOUR + 1 }, (_, i) => START_HOUR + i);

function lastNDays(n: number): string[] {
  const days: string[] = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  return days;
}

function intensity(score: number | null): string {
  if (score == null) return "bg-gray-50 dark:bg-white/[0.02]";
  if (score >= 80) return "bg-success-600";
  if (score >= 60) return "bg-success-400";
  if (score >= 40) return "bg-warning-400";
  if (score >= 20) return "bg-error-300";
  return "bg-error-500";
}

export default function PeakHoursHeatmap({ cells }: PeakHoursHeatmapProps) {
  const days = lastNDays(7);
  const byKey = new Map(cells.map((c) => [`${c.date}-${c.hour}`, c.focus_score]));

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[520px]">
        <div className="ml-12 grid grid-cols-7 gap-1 pb-1">
          {days.map((d) => (
            <div key={d} className="text-center text-theme-xs text-gray-400">
              {new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { weekday: "short" })}
            </div>
          ))}
        </div>
        {HOURS.map((hour) => (
          <div key={hour} className="mb-1 flex items-center gap-1">
            <span className="w-11 shrink-0 text-right text-theme-xs text-gray-400">
              {hour % 12 === 0 ? 12 : hour % 12}
              {hour < 12 ? "am" : "pm"}
            </span>
            <div className="grid flex-1 grid-cols-7 gap-1">
              {days.map((d) => {
                const score = byKey.get(`${d}-${hour}`) ?? null;
                return (
                  <div
                    key={d}
                    className={`h-5 rounded-sm ${intensity(score)}`}
                    title={`${d} ${hour}:00 — ${score != null ? Math.round(score) + "%" : "no data"}`}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
