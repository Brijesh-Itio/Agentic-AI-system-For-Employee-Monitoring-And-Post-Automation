import { useMemo, useState } from "react";
import { eachDayOfInterval, endOfMonth, endOfWeek, format, isSameMonth, isToday, startOfMonth, startOfWeek } from "date-fns";

import type { AttendanceDay, AttendanceStatus } from "@/api";

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Full background tint per status — the calendar's whole point is reading
// the month's shape at a glance, so colour carries the meaning, not a
// badge you'd have to read one cell at a time.
const STATUS_CELL_CLASSES: Record<AttendanceStatus, string> = {
  full_day: "bg-success-50 dark:bg-success-500/15 text-success-700 dark:text-success-400",
  half_day: "bg-warning-50 dark:bg-warning-500/15 text-warning-700 dark:text-warning-400",
  absent: "bg-error-50 dark:bg-error-500/15 text-error-700 dark:text-error-400",
  week_off: "bg-gray-50 dark:bg-white/[0.03] text-gray-400 dark:text-gray-500",
  upcoming: "bg-white dark:bg-transparent text-gray-300 dark:text-gray-600 border-dashed",
};

const STATUS_DOT_CLASSES: Record<AttendanceStatus, string> = {
  full_day: "bg-success-500",
  half_day: "bg-warning-500",
  absent: "bg-error-500",
  week_off: "bg-gray-400",
  upcoming: "bg-gray-200 dark:bg-gray-700",
};

interface AttendanceCalendarProps {
  month: string; // YYYY-MM
  days: AttendanceDay[];
  statusFilter: AttendanceStatus | "all";
  onSelectDay?: (day: AttendanceDay) => void;
}

function formatClock(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });
}

export default function AttendanceCalendar({ month, days, statusFilter, onSelectDay }: AttendanceCalendarProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const byDate = useMemo(() => new Map(days.map((d) => [d.date, d])), [days]);

  const [year, mon] = month.split("-").map(Number);
  const monthStart = startOfMonth(new Date(year, mon - 1, 1));
  const gridStart = startOfWeek(monthStart);
  const gridEnd = endOfWeek(endOfMonth(monthStart));
  const cells = eachDayOfInterval({ start: gridStart, end: gridEnd });

  return (
    <div>
      <div className="mb-1.5 grid grid-cols-7 gap-1.5 text-center text-theme-xs font-medium text-gray-400">
        {WEEKDAY_LABELS.map((w) => (
          <span key={w}>{w}</span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1.5">
        {cells.map((cellDate) => {
          const dateStr = format(cellDate, "yyyy-MM-dd");
          const day = byDate.get(dateStr);
          const inMonth = isSameMonth(cellDate, monthStart);
          const dimmed = statusFilter !== "all" && day && day.status !== statusFilter;

          return (
            <div
              key={dateStr}
              className="relative"
              onMouseEnter={() => inMonth && setHovered(dateStr)}
              onMouseLeave={() => setHovered((h) => (h === dateStr ? null : h))}
            >
              <button
                type="button"
                disabled={!inMonth || !day}
                onClick={() => day && onSelectDay?.(day)}
                className={`flex h-12 w-full flex-col items-center justify-center gap-0.5 rounded-lg border text-left transition-opacity sm:h-14 ${
                  inMonth
                    ? `border-gray-100 dark:border-gray-800 ${day ? STATUS_CELL_CLASSES[day.status] : ""}`
                    : "border-transparent opacity-0"
                } ${dimmed ? "opacity-30" : ""} ${isToday(cellDate) ? "ring-2 ring-brand-400 ring-inset" : ""}`}
              >
                <span className="text-theme-xs font-semibold">{format(cellDate, "d")}</span>
                {day && day.status !== "upcoming" && day.status !== "week_off" && (
                  <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT_CLASSES[day.status]}`} />
                )}
              </button>

              {hovered === dateStr && day && day.status !== "upcoming" && (
                <div className="absolute left-1/2 top-full z-20 mt-1.5 w-44 -translate-x-1/2 rounded-lg border border-gray-200 bg-white p-2.5 text-theme-xs shadow-xl dark:border-gray-700 dark:bg-gray-900">
                  <p className="mb-1 font-semibold text-gray-900 dark:text-white">
                    {format(cellDate, "EEEE, MMM d")}
                  </p>
                  {day.status === "week_off" ? (
                    <p className="text-gray-500 dark:text-gray-400">{day.week_off_reason ?? "Week off"}</p>
                  ) : (
                    <div className="space-y-0.5 text-gray-500 dark:text-gray-400">
                      <p>
                        In / Out: {formatClock(day.check_in)} – {formatClock(day.check_out)}
                      </p>
                      <p>Active: {day.active_hours_formatted}</p>
                      <p>Focus: {day.focus_score != null ? `${Math.round(day.focus_score)}%` : "—"}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
