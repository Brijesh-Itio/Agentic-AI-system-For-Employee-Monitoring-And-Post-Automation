import type { AttendanceDay } from "@/api";

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

interface WeeklyConsistencyProps {
  days: AttendanceDay[];
}

function toneFor(pct: number): string {
  if (pct >= 80) return "bg-success-500";
  if (pct >= 50) return "bg-warning-400";
  return "bg-error-400";
}

/** Which weekdays tend to slip — grouping the month's tracked days (working
 * days only, week-offs/upcoming excluded) by day-of-week surfaces a pattern
 * a plain calendar grid can't (e.g. "Mondays are consistently half-days"). */
export default function WeeklyConsistency({ days }: WeeklyConsistencyProps) {
  const buckets = Array.from({ length: 7 }, () => ({ credit: 0, tracked: 0 }));

  for (const d of days) {
    if (d.status === "week_off" || d.status === "upcoming") continue;
    const weekday = new Date(`${d.date}T00:00:00`).getDay();
    buckets[weekday].tracked += 1;
    if (d.status === "full_day") buckets[weekday].credit += 1;
    else if (d.status === "half_day") buckets[weekday].credit += 0.5;
  }

  return (
    <div>
      <div className="flex items-end gap-2">
        {buckets.map((b, i) => {
          const pct = b.tracked > 0 ? Math.round((b.credit / b.tracked) * 100) : null;
          return (
            <div key={i} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="flex h-20 w-full items-end rounded-md bg-gray-50 dark:bg-white/[0.03]">
                <div
                  className={`w-full rounded-md transition-all ${pct != null ? toneFor(pct) : ""}`}
                  style={{ height: pct != null ? `${Math.max(pct, 6)}%` : "0%" }}
                  title={pct != null ? `${WEEKDAY_LABELS[i]}: ${pct}% (${b.tracked} tracked)` : `${WEEKDAY_LABELS[i]}: no data`}
                />
              </div>
              <span className="text-theme-xs text-gray-400">{WEEKDAY_LABELS[i]}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
