import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlarmClock,
  Calendar1,
  CalendarClock,
  CalendarX,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  Flame,
  LayoutGrid,
  List,
  Loader2,
  Trophy,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { MONTHLY_LATE_WARNING_THRESHOLD } from "@/api";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import StatStrip from "@/components/common/StatStrip";
import AttendanceCalendar from "@/components/Attendance/AttendanceCalendar";
import AttendanceDayDrawer from "@/components/Attendance/AttendanceDayDrawer";
import HolidayManager from "@/components/Attendance/HolidayManager";
import WeeklyConsistency from "@/components/Attendance/WeeklyConsistency";
import MonthPicker from "@/components/Attendance/MonthPicker";
import { STATUS_META } from "@/components/Attendance/statusMeta";
import { getMyAttendance, type AttendanceDay, type AttendanceStatus } from "@/api";

const STATUS_FILTERS: { value: AttendanceStatus | "all"; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "full_day", label: "Full Day" },
  { value: "half_day", label: "Half Day" },
  { value: "absent", label: "Absent" },
  { value: "week_off", label: "Week Off" },
  { value: "upcoming", label: "Upcoming" },
];

const LEGEND: { status: AttendanceStatus; label: string; dot: string }[] = [
  { status: "full_day", label: "Full Day", dot: "bg-success-500" },
  { status: "half_day", label: "Half Day", dot: "bg-warning-500" },
  { status: "absent", label: "Absent", dot: "bg-error-500" },
  { status: "week_off", label: "Week Off", dot: "bg-gray-400" },
];

function shiftMonth(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const d = new Date(year, mon - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function formatClock(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });
}

function dayName(dateStr: string): string {
  return new Date(`${dateStr}T00:00:00`).toLocaleDateString(undefined, { weekday: "short" });
}

function attendanceRateOf(summary: { full_days: number; half_days: number; absents: number } | undefined): number | null {
  if (!summary) return null;
  const tracked = summary.full_days + summary.half_days + summary.absents;
  if (tracked === 0) return null;
  return Math.round(((summary.full_days + summary.half_days * 0.5) / tracked) * 100);
}

/** Current streak = consecutive attended working days trailing up to today
 * (or the last past day in the month); longest = the best run anywhere in
 * the month. Week-offs/upcoming days neither extend nor break a streak —
 * only an actual absence does. */
function computeStreaks(days: AttendanceDay[]): { current: number; longest: number } {
  const today = new Date().toISOString().slice(0, 10);
  let running = 0;
  let longest = 0;

  for (const d of days) {
    if (d.date > today) break;
    if (d.status === "full_day" || d.status === "half_day") {
      running += 1;
      longest = Math.max(longest, running);
    } else if (d.status === "absent") {
      running = 0;
    }
  }
  return { current: running, longest };
}

export default function AttendancePage() {
  const [month, setMonth] = useState(currentMonth());
  const [statusFilter, setStatusFilter] = useState<AttendanceStatus | "all">("all");
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [selectedDay, setSelectedDay] = useState<AttendanceDay | null>(null);
  const isCurrentMonth = month === currentMonth();
  const previousMonth = shiftMonth(month, -1);

  const query = useQuery({
    queryKey: ["attendance", "me", month],
    queryFn: () => getMyAttendance(month),
  });
  // Powers the "vs last month" trend on the hero card — a second cheap
  // call to the same endpoint, not a new backend capability.
  const previousQuery = useQuery({
    queryKey: ["attendance", "me", previousMonth],
    queryFn: () => getMyAttendance(previousMonth),
  });

  const days: AttendanceDay[] = query.data?.days ?? [];
  const filteredDays = useMemo(
    () => (statusFilter === "all" ? days : days.filter((d) => d.status === statusFilter)),
    [days, statusFilter]
  );

  // Attendance rate: half days count for half credit, week-offs/upcoming
  // don't count against you either way since they're not working days.
  const trackedWorkingDays = (query.data?.full_days ?? 0) + (query.data?.half_days ?? 0) + (query.data?.absents ?? 0);
  const attendanceRate = attendanceRateOf(query.data);
  const previousRate = attendanceRateOf(previousQuery.data);
  const rateDelta = attendanceRate != null && previousRate != null ? attendanceRate - previousRate : null;
  const streaks = useMemo(() => computeStreaks(days), [days]);

  const handleExportCsv = () => {
    const header = ["Date", "Day", "Check In", "Late", "Check Out", "Active Hours", "Focus Score", "Status"];
    const rows = filteredDays.map((d) => [
      d.date,
      dayName(d.date),
      formatClock(d.check_in),
      d.is_late ? "Yes" : "No",
      formatClock(d.check_out),
      d.active_hours_formatted,
      d.focus_score != null ? `${Math.round(d.focus_score)}%` : "",
      STATUS_META[d.status].label,
    ]);
    const csv = [header, ...rows].map((r) => r.map((cell) => `"${cell}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance-${month}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageMeta title="Attendance | WorkPulse AI" description="Automatically tracked daily attendance, check-in/check-out, and focus." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Attendance</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Automatically derived from your tracked activity — no manual check-in required. Every Sunday and the
              1st/3rd Saturday of each month are paid week-offs.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMonth((m) => shiftMonth(m, -1))}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
              aria-label="Previous month"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <MonthPicker month={month} onChange={setMonth} maxMonth={currentMonth()} />
            <button
              onClick={() => setMonth((m) => shiftMonth(m, 1))}
              disabled={isCurrentMonth}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
              aria-label="Next month"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Hero: attendance rate for the month */}
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-indigo-600 px-5 py-4 text-white shadow-md shadow-brand-500/20">
          <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
          <div className="relative flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <p className="text-3xl font-bold">{attendanceRate != null ? `${attendanceRate}%` : "—"}</p>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-theme-sm font-medium text-white/80">Attendance rate</p>
                  {rateDelta !== null && rateDelta !== 0 && (
                    <span
                      className={`flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                        rateDelta > 0 ? "bg-white/20 text-white" : "bg-black/15 text-white/90"
                      }`}
                    >
                      {rateDelta > 0 ? (
                        <TrendingUp className="h-2.5 w-2.5" />
                      ) : (
                        <TrendingDown className="h-2.5 w-2.5" />
                      )}
                      {Math.abs(rateDelta)}pts vs last month
                    </span>
                  )}
                </div>
                <p className="text-theme-xs text-white/70">
                  {trackedWorkingDays > 0
                    ? `${trackedWorkingDays} working day${trackedWorkingDays === 1 ? "" : "s"} so far`
                    : "No working days tracked yet"}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {LEGEND.map((l) => (
                <div key={l.status} className="flex items-center gap-1.5 text-theme-xs text-white/90">
                  <span className={`h-2 w-2 rounded-full ${l.dot}`} />
                  {l.label}
                </div>
              ))}
            </div>
          </div>
        </div>

        <StatStrip
          stats={[
            {
              label: "Full Days",
              value: String(query.data?.full_days ?? 0),
              icon: CheckCircle2,
              valueClassName: "text-success-600 dark:text-success-400",
              loading: query.isLoading,
            },
            {
              label: "Half Days",
              value: String(query.data?.half_days ?? 0),
              icon: CalendarClock,
              valueClassName: "text-warning-600 dark:text-warning-400",
              loading: query.isLoading,
            },
            {
              label: "Absent",
              value: String(query.data?.absents ?? 0),
              icon: CalendarX,
              valueClassName: "text-error-600 dark:text-error-400",
              loading: query.isLoading,
            },
            {
              label: "Week Offs",
              value: String(query.data?.week_offs ?? 0),
              icon: Calendar1,
              loading: query.isLoading,
            },
            {
              label: "Late Arrivals",
              value: `${query.data?.late_count ?? 0} / ${MONTHLY_LATE_WARNING_THRESHOLD}`,
              hint: "this month — outside punch-in windows",
              icon: AlarmClock,
              valueClassName:
                (query.data?.late_count ?? 0) >= MONTHLY_LATE_WARNING_THRESHOLD
                  ? "text-orange-600 dark:text-orange-400"
                  : undefined,
              loading: query.isLoading,
            },
            {
              label: "Current Streak",
              value: `${streaks.current}d`,
              hint: "consecutive attended days",
              icon: Flame,
              valueClassName: streaks.current > 0 ? "text-success-600 dark:text-success-400" : undefined,
              loading: query.isLoading,
            },
            {
              label: "Best Streak",
              value: `${streaks.longest}d`,
              hint: "this month",
              icon: Trophy,
              loading: query.isLoading,
            },
          ]}
        />

        <HolidayManager />

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500 dark:text-gray-400">Weekly Consistency</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {query.isLoading ? (
              <div className="flex h-24 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              <WeeklyConsistency days={days} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
            <CardTitle>{view === "calendar" ? "Calendar" : "Daily Log"}</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as AttendanceStatus | "all")}
                className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
              >
                {STATUS_FILTERS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
              <div className="flex items-center rounded-lg border border-gray-300 p-0.5 dark:border-gray-700">
                <button
                  onClick={() => setView("calendar")}
                  className={`flex h-7 w-7 items-center justify-center rounded-md ${
                    view === "calendar"
                      ? "bg-brand-500 text-white"
                      : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
                  }`}
                  aria-label="Calendar view"
                >
                  <LayoutGrid className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => setView("list")}
                  className={`flex h-7 w-7 items-center justify-center rounded-md ${
                    view === "list"
                      ? "bg-brand-500 text-white"
                      : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
                  }`}
                  aria-label="List view"
                >
                  <List className="h-3.5 w-3.5" />
                </button>
              </div>
              <button
                onClick={handleExportCsv}
                disabled={filteredDays.length === 0}
                className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
              >
                <Download className="h-3.5 w-3.5" />
                Export CSV
              </button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {query.isLoading ? (
              <div className="flex h-48 items-center justify-center text-gray-400">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : view === "calendar" ? (
              <AttendanceCalendar month={month} days={days} statusFilter={statusFilter} onSelectDay={setSelectedDay} />
            ) : filteredDays.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-gray-400">
                <CalendarX className="h-9 w-9" />
                <p className="text-theme-sm font-medium text-gray-500 dark:text-gray-400">
                  No days match this filter.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-800">
                <table className="w-full text-left text-theme-sm">
                  <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500 dark:bg-gray-900 dark:text-gray-400">
                    <tr>
                      <th className="px-3 py-2.5">Date</th>
                      <th className="px-3 py-2.5">Day</th>
                      <th className="px-3 py-2.5">Check In</th>
                      <th className="px-3 py-2.5">Check Out</th>
                      <th className="px-3 py-2.5">Active Hours</th>
                      <th className="px-3 py-2.5">Focus</th>
                      <th className="px-3 py-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDays.map((d) => {
                      const meta = STATUS_META[d.status];
                      return (
                        <tr
                          key={d.date}
                          onClick={() => setSelectedDay(d)}
                          className="cursor-pointer border-t border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-white/5"
                        >
                          <td className="px-3 py-2 font-medium text-gray-900 dark:text-white">{d.date}</td>
                          <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{dayName(d.date)}</td>
                          <td className="px-3 py-2">
                            {formatClock(d.check_in)}
                            {d.is_late && (
                              <span className="ml-1.5 rounded-full bg-orange-50 px-1.5 py-0.5 text-theme-xs font-medium text-orange-600 dark:bg-orange-500/10 dark:text-orange-400">
                                Late
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            {formatClock(d.check_out)}
                            {d.is_half_day_checkout && (
                              <span className="ml-1.5 rounded-full bg-blue-50 px-1.5 py-0.5 text-theme-xs font-medium text-blue-600 dark:bg-blue-500/10 dark:text-blue-400">
                                Half-day
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2">{d.active_hours_formatted}</td>
                          <td className="px-3 py-2">{d.focus_score != null ? `${Math.round(d.focus_score)}%` : "—"}</td>
                          <td className="px-3 py-2">
                            <Badge variant={meta.variant} title={d.week_off_reason ?? undefined}>
                              {meta.label}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedDay && <AttendanceDayDrawer day={selectedDay} onClose={() => setSelectedDay(null)} />}
    </>
  );
}
