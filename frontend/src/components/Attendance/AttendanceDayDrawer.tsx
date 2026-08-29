import { X, ArrowRight } from "lucide-react";
import { Link } from "react-router";
import type { AttendanceDay } from "@/api";
import { Badge } from "@/components/shadcn/badge";
import { STATUS_META } from "./statusMeta";

function formatClock(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });
}

interface AttendanceDayDrawerProps {
  day: AttendanceDay;
  onClose: () => void;
}

export default function AttendanceDayDrawer({ day, onClose }: AttendanceDayDrawerProps) {
  const meta = STATUS_META[day.status];
  const dateLabel = new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  const hasActivity = day.status !== "week_off" && day.status !== "upcoming";

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-sm border-l border-gray-200 bg-white p-5 shadow-2xl dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">{dateLabel}</h3>
          <Badge variant={meta.variant} className="mt-1.5">
            {meta.label}
          </Badge>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-white/5"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5 space-y-4 text-sm">
        {day.status === "week_off" ? (
          <p className="text-gray-500 dark:text-gray-400">{day.week_off_reason ?? "Week off"}</p>
        ) : day.status === "upcoming" ? (
          <p className="text-gray-500 dark:text-gray-400">This day hasn't happened yet.</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-theme-xs font-medium uppercase text-gray-400">Check In</p>
                <p className="mt-1 text-gray-700 dark:text-gray-300">
                  {formatClock(day.check_in)}
                  {day.is_late && (
                    <span className="ml-1.5 rounded-full bg-orange-50 px-1.5 py-0.5 text-theme-xs font-medium text-orange-600 dark:bg-orange-500/10 dark:text-orange-400">
                      Late
                    </span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-theme-xs font-medium uppercase text-gray-400">Check Out</p>
                <p className="mt-1 text-gray-700 dark:text-gray-300">
                  {formatClock(day.check_out)}
                  {day.is_half_day_checkout && (
                    <span className="ml-1.5 rounded-full bg-blue-50 px-1.5 py-0.5 text-theme-xs font-medium text-blue-600 dark:bg-blue-500/10 dark:text-blue-400">
                      Half-day
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-theme-xs font-medium uppercase text-gray-400">Active Time</p>
                <p className="mt-1 text-gray-700 dark:text-gray-300">{day.active_hours_formatted}</p>
              </div>
              <div>
                <p className="text-theme-xs font-medium uppercase text-gray-400">Focus Score</p>
                <p className="mt-1 text-gray-700 dark:text-gray-300">
                  {day.focus_score != null ? `${Math.round(day.focus_score)}%` : "—"}
                </p>
              </div>
            </div>
          </>
        )}

        {hasActivity && (
          <Link
            to={`/timeline?date=${day.date}`}
            className="mt-2 flex items-center justify-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 py-2 text-theme-sm font-medium text-brand-600 transition-colors hover:bg-brand-100 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-400 dark:hover:bg-brand-500/20"
          >
            View full timeline
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>
    </div>
  );
}
