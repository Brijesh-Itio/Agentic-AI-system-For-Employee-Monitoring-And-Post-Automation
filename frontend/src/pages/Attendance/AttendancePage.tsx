import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar1,
  CalendarClock,
  CalendarX,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  List,
  Loader2,
} from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import StatCard from "@/components/dashboard/StatCard";
import AttendanceCalendar from "@/components/Attendance/AttendanceCalendar";
import MonthPicker from "@/components/Attendance/MonthPicker";
import { getMyAttendance, type AttendanceDay, type AttendanceStatus } from "@/api";

const STATUS_META: Record<AttendanceStatus, { label: string; variant: "success" | "warning" | "destructive" | "outline" | "default" }> = {
  full_day: { label: "Full Day", variant: "success" },
  half_day: { label: "Half Day", variant: "warning" },
  absent: { label: "Absent", variant: "destructive" },
  week_off: { label: "Week Off", variant: "outline" },
  upcoming: { label: "Upcoming", variant: "outline" },
};

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

export default function AttendancePage() {
  const [month, setMonth] = useState(currentMonth());
  const [statusFilter, setStatusFilter] = useState<AttendanceStatus | "all">("all");
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const isCurrentMonth = month === currentMonth();

  const query = useQuery({
    queryKey: ["attendance", "me", month],
    queryFn: () => getMyAttendance(month),
  });

  const days: AttendanceDay[] = query.data?.days ?? [];
  const filteredDays = useMemo(
    () => (statusFilter === "all" ? days : days.filter((d) => d.status === statusFilter)),
    [days, statusFilter]
  );

  // Attendance rate: half days count for half credit, week-offs/upcoming
  // don't count against you either way since they're not working days.
  const trackedWorkingDays = (query.data?.full_days ?? 0) + (query.data?.half_days ?? 0) + (query.data?.absents ?? 0);
  const attendanceRate =
    trackedWorkingDays > 0
      ? Math.round((((query.data?.full_days ?? 0) + (query.data?.half_days ?? 0) * 0.5) / trackedWorkingDays) * 100)
      : null;

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
                <p className="text-theme-sm font-medium text-white/80">Attendance rate</p>
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

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label="Full Days"
            value={query.isLoading ? "—" : String(query.data?.full_days ?? 0)}
            icon={CheckCircle2}
            tone="success"
            loading={query.isLoading}
          />
          <StatCard
            label="Half Days"
            value={query.isLoading ? "—" : String(query.data?.half_days ?? 0)}
            icon={CalendarClock}
            tone="warning"
            loading={query.isLoading}
          />
          <StatCard
            label="Absent"
            value={query.isLoading ? "—" : String(query.data?.absents ?? 0)}
            icon={CalendarX}
            tone="error"
            loading={query.isLoading}
          />
          <StatCard
            label="Week Offs"
            value={query.isLoading ? "—" : String(query.data?.week_offs ?? 0)}
            icon={Calendar1}
            loading={query.isLoading}
          />
        </div>

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
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {query.isLoading ? (
              <div className="flex h-48 items-center justify-center text-gray-400">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : view === "calendar" ? (
              <AttendanceCalendar month={month} days={days} statusFilter={statusFilter} />
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
                          className="border-t border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-white/5"
                        >
                          <td className="px-3 py-2 font-medium text-gray-900 dark:text-white">{d.date}</td>
                          <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{dayName(d.date)}</td>
                          <td className="px-3 py-2">{formatClock(d.check_in)}</td>
                          <td className="px-3 py-2">{formatClock(d.check_out)}</td>
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
    </>
  );
}
