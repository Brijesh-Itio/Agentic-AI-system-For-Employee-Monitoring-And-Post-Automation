import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeft,
  Calendar1,
  CalendarClock,
  CalendarX,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Crown,
  FileText,
  ImageOff,
  LayoutGrid,
  List,
  Loader2,
  Repeat2,
  Target,
  TrendingUp,
} from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Badge } from "@/components/shadcn/badge";
import { Card, CardContent } from "@/components/shadcn/card";
import StatCard from "@/components/dashboard/StatCard";
import AttendanceCalendar from "@/components/Attendance/AttendanceCalendar";
import TimelineTrack from "@/components/Timeline/TimelineTrack";
import ScreenshotGrid from "@/components/Screenshots/ScreenshotGrid";
import ScreenshotDetailModal from "@/components/Screenshots/ScreenshotDetailModal";
import ReportsList from "@/components/Reports/ReportsList";
import DarContent from "@/components/Reports/DarContent";
import AdminControls from "@/components/Team/AdminControls";
import FeatureToggles from "@/components/Team/FeatureToggles";
import {
  getMemberActivity,
  getMemberAttendance,
  getMemberDars,
  getMemberScreenshotsByDate,
  getTeamOverview,
  type ActivityLogEntry,
  type AttendanceDay,
  type AttendanceStatus,
  type DarReport,
  type IdlePeriod,
  type MemberStatus,
  type ScreenshotEntry,
} from "@/api";
import { CATEGORY_COLOR, CATEGORY_LABEL, computeDayBounds, formatDuration } from "@/components/Timeline/timeScale";
import { useAuth } from "@/context/AuthContext";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

const statTone: Record<MemberStatus, "neutral" | "success" | "warning" | "error"> = {
  active: "success",
  idle: "warning",
  offline: "neutral",
};

const todayStr = () => new Date().toISOString().slice(0, 10);
const currentMonth = () => todayStr().slice(0, 7);

// Refresh cadence for the "live" tabs while an admin/manager is actively
// looking at this employee — matches TeamPage's own 60s overview refresh.
const LIVE_REFETCH_MS = 30_000;

const CATEGORY_VARIANT = {
  productive: "success",
  neutral: "default",
  distraction: "destructive",
  uncategorised: "outline",
} as const;

const ATTENDANCE_VARIANT: Record<string, "success" | "warning" | "destructive" | "outline" | "default"> = {
  full_day: "success",
  half_day: "warning",
  absent: "destructive",
  week_off: "outline",
  upcoming: "outline",
};

const STATUS_FILTERS: { value: AttendanceStatus | "all"; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "full_day", label: "Full Day" },
  { value: "half_day", label: "Half Day" },
  { value: "absent", label: "Absent" },
  { value: "week_off", label: "Week Off" },
];

const LEGEND: { status: AttendanceStatus; label: string; dot: string }[] = [
  { status: "full_day", label: "Full Day", dot: "bg-success-500" },
  { status: "half_day", label: "Half Day", dot: "bg-warning-500" },
  { status: "absent", label: "Absent", dot: "bg-error-500" },
  { status: "week_off", label: "Week Off", dot: "bg-gray-400" },
];

function formatClock(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });
}

// Stable empty-array references so components/hooks receiving these as
// props or deps don't see a "changed" array (and re-render/recompute) on
// every render just because `data ?? []` allocates a fresh one each time.
const EMPTY_SESSIONS: ActivityLogEntry[] = [];
const EMPTY_IDLE_PERIODS: IdlePeriod[] = [];
const EMPTY_SCREENSHOTS: ScreenshotEntry[] = [];
const EMPTY_DARS: DarReport[] = [];
const EMPTY_ATTENDANCE_DAYS: AttendanceDay[] = [];

function shiftMonth(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const d = new Date(year, mon - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

type Tab = "overview" | "screenshots" | "attendance" | "reports";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "screenshots", label: "Screenshots" },
  { id: "attendance", label: "Attendance" },
  { id: "reports", label: "DAR Reports" },
];

export default function TeamMemberProfilePage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const { isAdmin, user: currentUser } = useAuth();

  const [tab, setTab] = useState<Tab>("overview");
  const [date, setDate] = useState(todayStr());
  const [month, setMonth] = useState(currentMonth());
  const [attendanceView, setAttendanceView] = useState<"calendar" | "list">("calendar");
  const [statusFilter, setStatusFilter] = useState<AttendanceStatus | "all">("all");
  const [selectedDarDate, setSelectedDarDate] = useState<string | null>(null);
  const [selectedShotIndex, setSelectedShotIndex] = useState<number | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["team", "overview"],
    queryFn: getTeamOverview,
    refetchInterval: LIVE_REFETCH_MS,
  });
  const member = overviewQuery.data?.find((m) => m.user.id === userId) ?? null;

  const activityQuery = useQuery({
    queryKey: ["team", "member-activity", userId, date],
    queryFn: () => getMemberActivity(userId!, date),
    enabled: userId != null && tab === "overview",
    refetchInterval: tab === "overview" ? LIVE_REFETCH_MS : false,
  });

  const screenshotsQuery = useQuery({
    queryKey: ["team", "member-screenshots", userId, date],
    queryFn: () => getMemberScreenshotsByDate(userId!, date),
    enabled: userId != null && tab === "screenshots",
    refetchInterval: tab === "screenshots" ? LIVE_REFETCH_MS : false,
  });

  const attendanceQuery = useQuery({
    queryKey: ["team", "member-attendance", userId, month],
    queryFn: () => getMemberAttendance(userId!, month),
    enabled: userId != null && tab === "attendance",
  });

  const darsQuery = useQuery({
    queryKey: ["team", "member-dars", userId],
    queryFn: () => getMemberDars(userId!),
    enabled: userId != null && tab === "reports",
  });
  const dars = darsQuery.data ?? EMPTY_DARS;
  useEffect(() => {
    if (!selectedDarDate && dars.length > 0) setSelectedDarDate(dars[0].date);
  }, [dars, selectedDarDate]);
  const selectedDar = dars.find((r) => r.date === selectedDarDate) ?? null;

  const activitySessions = useMemo(() => activityQuery.data ?? EMPTY_SESSIONS, [activityQuery.data]);
  const dayBounds = useMemo(
    () => computeDayBounds(date, activitySessions, EMPTY_IDLE_PERIODS),
    [date, activitySessions]
  );

  const daySummary = useMemo(() => {
    const totalSeconds = activitySessions.reduce((sum, s) => sum + (s.duration_seconds ?? 0), 0);
    const productiveSeconds = activitySessions
      .filter((s) => s.category === "productive")
      .reduce((sum, s) => sum + (s.duration_seconds ?? 0), 0);
    const byApp = new Map<string, number>();
    for (const s of activitySessions) {
      byApp.set(s.app_name, (byApp.get(s.app_name) ?? 0) + (s.duration_seconds ?? 0));
    }
    const topApps = Array.from(byApp.entries())
      .map(([app_name, seconds]) => ({
        app_name,
        seconds,
        category: activitySessions.find((s) => s.app_name === app_name)?.category ?? "uncategorised",
      }))
      .sort((a, b) => b.seconds - a.seconds)
      .slice(0, 5);
    return {
      totalSeconds,
      productivePct: totalSeconds > 0 ? Math.round((productiveSeconds / totalSeconds) * 100) : null,
      switchCount: activitySessions.length,
      topApp: topApps[0]?.app_name ?? null,
      topApps,
    };
  }, [activitySessions]);

  const selectedShot: ScreenshotEntry | null =
    selectedShotIndex != null ? screenshotsQuery.data?.[selectedShotIndex] ?? null : null;

  const attendanceDays: AttendanceDay[] = attendanceQuery.data?.days ?? EMPTY_ATTENDANCE_DAYS;
  const filteredAttendanceDays = useMemo(
    () => (statusFilter === "all" ? attendanceDays : attendanceDays.filter((d) => d.status === statusFilter)),
    [attendanceDays, statusFilter]
  );

  const attendanceRate = useMemo(() => {
    if (!attendanceQuery.data) return null;
    const { full_days, half_days, absents } = attendanceQuery.data;
    const worked = full_days + half_days + absents;
    return worked > 0 ? Math.round(((full_days + half_days * 0.5) / worked) * 100) : null;
  }, [attendanceQuery.data]);

  return (
    <>
      <PageMeta
        title={member ? `${member.user.name} | WorkPulse AI` : "Team Member | WorkPulse AI"}
        description="Individual team member activity, screenshots, attendance, and reports."
      />

      <div className="space-y-6">
        <Link
          to="/team"
          className="inline-flex items-center gap-1.5 text-theme-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Team
        </Link>

        {overviewQuery.isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : !member ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-gray-400">
              This team member could not be found.
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-brand-600 via-brand-500 to-indigo-600 px-5 py-5 text-white shadow-md shadow-brand-500/20">
              <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
              <div className="relative flex flex-wrap items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-white/15 text-lg font-semibold backdrop-blur-sm">
                  {initials(member.user.name)}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-xl font-bold">{member.user.name}</h1>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-medium capitalize backdrop-blur-sm`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          member.status === "active"
                            ? "bg-success-400"
                            : member.status === "idle"
                              ? "bg-warning-400"
                              : "bg-white/50"
                        }`}
                      />
                      {member.status}
                    </span>
                  </div>
                  <p className="text-theme-xs text-white/70">
                    {member.user.email ?? member.user.id} · {member.user.role}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <StatCard label="Status" value={member.status} icon={Activity} tone={statTone[member.status]} />
              <StatCard
                label="Focus Score"
                value={member.focus_score != null ? `${Math.round(member.focus_score)}%` : "—"}
                icon={Target}
                tone={
                  member.focus_score == null ? "neutral" : member.focus_score >= 70 ? "success" : member.focus_score >= 40 ? "warning" : "error"
                }
              />
              <StatCard label="Hours Today" value={`${member.active_hours_today}h`} icon={Clock} />
            </div>

            <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5 w-fit">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
                    tab === t.id
                      ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white"
                      : "text-gray-500"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <Card>
              <CardContent className="p-6">
                {tab === "overview" && (
                  <>
                    <div className="mb-4 flex justify-end">
                      <input
                        type="date"
                        value={date}
                        max={todayStr()}
                        onChange={(e) => setDate(e.target.value)}
                        className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-theme-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                      />
                    </div>
                    {activityQuery.isLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                      </div>
                    ) : !activityQuery.data || activityQuery.data.length === 0 ? (
                      <p className="py-8 text-center text-theme-sm text-gray-400">No tracked activity for this date.</p>
                    ) : (
                      <>
                        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                          <StatCard label="Active Time" value={formatDuration(daySummary.totalSeconds)} icon={Clock} />
                          <StatCard
                            label="Productive"
                            value={daySummary.productivePct != null ? `${daySummary.productivePct}%` : "—"}
                            icon={TrendingUp}
                            tone={
                              daySummary.productivePct == null
                                ? "neutral"
                                : daySummary.productivePct >= 70
                                  ? "success"
                                  : daySummary.productivePct >= 40
                                    ? "warning"
                                    : "error"
                            }
                          />
                          <StatCard label="App Switches" value={String(daySummary.switchCount)} icon={Repeat2} />
                          <StatCard label="Top App" value={daySummary.topApp ?? "—"} icon={Crown} />
                        </div>

                        <p className="mb-2 text-theme-xs font-medium uppercase tracking-wide text-gray-400">
                          Day Timeline
                        </p>
                        <TimelineTrack
                          bounds={dayBounds}
                          sessions={activitySessions}
                          idlePeriods={EMPTY_IDLE_PERIODS}
                          screenshots={EMPTY_SCREENSHOTS}
                          selectedSessionId={selectedSessionId}
                          onSelectSession={(s) => setSelectedSessionId(s.id)}
                          onSelectScreenshot={() => {}}
                        />

                        <div className="mb-2 mt-6 flex flex-wrap items-center gap-x-4 gap-y-1 text-theme-xs text-gray-400">
                          {(Object.keys(CATEGORY_LABEL) as (keyof typeof CATEGORY_LABEL)[]).map((cat) => (
                            <div key={cat} className="flex items-center gap-1.5">
                              <span className={`h-2 w-2 rounded-full ${CATEGORY_COLOR[cat]}`} />
                              {CATEGORY_LABEL[cat]}
                            </div>
                          ))}
                        </div>

                        {daySummary.topApps.length > 0 && (
                          <>
                            <p className="mb-2 mt-6 text-theme-xs font-medium uppercase tracking-wide text-gray-400">
                              Top Apps
                            </p>
                            <div className="mb-6 space-y-2">
                              {daySummary.topApps.map((a) => (
                                <div key={a.app_name} className="flex items-center gap-3">
                                  <span className="w-32 shrink-0 truncate text-theme-sm text-gray-700 dark:text-gray-300">
                                    {a.app_name}
                                  </span>
                                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100 dark:bg-white/5">
                                    <div
                                      className={`h-full rounded-full ${CATEGORY_COLOR[a.category]}`}
                                      style={{
                                        width: `${daySummary.totalSeconds > 0 ? Math.max(2, (a.seconds / daySummary.totalSeconds) * 100) : 0}%`,
                                      }}
                                    />
                                  </div>
                                  <span className="w-14 shrink-0 text-right text-theme-xs text-gray-400">
                                    {formatDuration(a.seconds)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </>
                        )}

                        <p className="mb-2 text-theme-xs font-medium uppercase tracking-wide text-gray-400">
                          Session Log
                        </p>
                        <div className="max-h-[24rem] overflow-y-auto rounded-xl border border-gray-100 dark:border-gray-800">
                          <table className="w-full text-left text-theme-sm">
                            <thead className="sticky top-0 bg-gray-50 text-xs uppercase tracking-wide text-gray-500 dark:bg-gray-900 dark:text-gray-400">
                              <tr>
                                <th className="px-3 py-2.5">App</th>
                                <th className="px-3 py-2.5">Time</th>
                                <th className="px-3 py-2.5">Duration</th>
                                <th className="px-3 py-2.5">Category</th>
                              </tr>
                            </thead>
                            <tbody>
                              {activityQuery.data.map((entry) => (
                                <tr
                                  key={entry.id}
                                  onClick={() => setSelectedSessionId(entry.id)}
                                  className={`cursor-pointer border-t border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-white/5 ${
                                    selectedSessionId === entry.id ? "bg-brand-50/60 dark:bg-brand-500/10" : ""
                                  }`}
                                >
                                  <td className="px-3 py-2 truncate max-w-[220px]">{entry.app_name}</td>
                                  <td className="px-3 py-2 whitespace-nowrap text-gray-400">
                                    {new Date(entry.start_time).toLocaleTimeString(undefined, {
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })}
                                  </td>
                                  <td className="px-3 py-2 whitespace-nowrap">
                                    {entry.duration_seconds != null ? formatDuration(entry.duration_seconds) : "—"}
                                  </td>
                                  <td className="px-3 py-2">
                                    <Badge variant={CATEGORY_VARIANT[entry.category]}>{entry.category}</Badge>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </>
                )}

                {tab === "screenshots" && (
                  <>
                    <div className="mb-4 flex justify-end">
                      <input
                        type="date"
                        value={date}
                        max={todayStr()}
                        onChange={(e) => setDate(e.target.value)}
                        className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-theme-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                      />
                    </div>
                    {screenshotsQuery.isLoading ? (
                      <div className="flex h-48 items-center justify-center text-gray-400">
                        <Loader2 className="h-6 w-6 animate-spin" />
                      </div>
                    ) : !screenshotsQuery.data || screenshotsQuery.data.length === 0 ? (
                      <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-gray-400">
                        <ImageOff className="h-9 w-9" />
                        <p className="text-theme-sm font-medium text-gray-500 dark:text-gray-400">
                          No screenshots captured for this day
                        </p>
                      </div>
                    ) : (
                      <ScreenshotGrid
                        screenshots={screenshotsQuery.data}
                        sessions={EMPTY_SESSIONS}
                        selectedId={selectedShot?.id ?? null}
                        onSelect={(shot) =>
                          setSelectedShotIndex(screenshotsQuery.data!.findIndex((s) => s.id === shot.id))
                        }
                      />
                    )}
                  </>
                )}

                {tab === "attendance" && (
                  <>
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-10 min-w-[3.5rem] items-center justify-center rounded-lg bg-brand-50 px-2 text-sm font-bold text-brand-600 dark:bg-brand-500/10 dark:text-brand-400">
                          {attendanceRate != null ? `${attendanceRate}%` : "—"}
                        </div>
                        <div>
                          <p className="text-theme-sm font-medium text-gray-700 dark:text-gray-300">Attendance rate</p>
                          <p className="text-theme-xs text-gray-400">
                            {attendanceQuery.data
                              ? `${attendanceQuery.data.full_days + attendanceQuery.data.half_days + attendanceQuery.data.absents} working day(s) tracked`
                              : "No data for this month yet"}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => setMonth((m) => shiftMonth(m, -1))}
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
                          aria-label="Previous month"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>
                        <input
                          type="month"
                          value={month}
                          max={currentMonth()}
                          onChange={(e) => setMonth(e.target.value)}
                          className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-theme-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
                        />
                        <button
                          onClick={() => setMonth((m) => shiftMonth(m, 1))}
                          disabled={month === currentMonth()}
                          className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
                          aria-label="Next month"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <StatCard
                        label="Full Days"
                        value={String(attendanceQuery.data?.full_days ?? 0)}
                        icon={CheckCircle2}
                        tone="success"
                        loading={attendanceQuery.isLoading}
                      />
                      <StatCard
                        label="Half Days"
                        value={String(attendanceQuery.data?.half_days ?? 0)}
                        icon={CalendarClock}
                        tone="warning"
                        loading={attendanceQuery.isLoading}
                      />
                      <StatCard
                        label="Absent"
                        value={String(attendanceQuery.data?.absents ?? 0)}
                        icon={CalendarX}
                        tone="error"
                        loading={attendanceQuery.isLoading}
                      />
                      <StatCard
                        label="Week Offs"
                        value={String(attendanceQuery.data?.week_offs ?? 0)}
                        icon={Calendar1}
                        loading={attendanceQuery.isLoading}
                      />
                    </div>

                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        {LEGEND.map((l) => (
                          <div key={l.status} className="flex items-center gap-1.5 text-theme-xs text-gray-500 dark:text-gray-400">
                            <span className={`h-2 w-2 rounded-full ${l.dot}`} />
                            {l.label}
                          </div>
                        ))}
                      </div>
                      <div className="flex items-center gap-2">
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
                            onClick={() => setAttendanceView("calendar")}
                            className={`flex h-7 w-7 items-center justify-center rounded-md ${
                              attendanceView === "calendar"
                                ? "bg-brand-500 text-white"
                                : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
                            }`}
                            aria-label="Calendar view"
                          >
                            <LayoutGrid className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setAttendanceView("list")}
                            className={`flex h-7 w-7 items-center justify-center rounded-md ${
                              attendanceView === "list"
                                ? "bg-brand-500 text-white"
                                : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
                            }`}
                            aria-label="List view"
                          >
                            <List className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {attendanceQuery.isLoading ? (
                      <div className="flex h-48 items-center justify-center text-gray-400">
                        <Loader2 className="h-6 w-6 animate-spin" />
                      </div>
                    ) : attendanceView === "calendar" ? (
                      <AttendanceCalendar month={month} days={attendanceDays} statusFilter={statusFilter} />
                    ) : filteredAttendanceDays.length === 0 ? (
                      <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-gray-400">
                        <CalendarX className="h-9 w-9" />
                        <p className="text-theme-sm font-medium text-gray-500 dark:text-gray-400">No days match this filter.</p>
                      </div>
                    ) : (
                      <div className="max-h-[28rem] overflow-y-auto overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-800">
                        <table className="w-full text-left text-theme-sm">
                          <thead className="sticky top-0 bg-gray-50 text-xs uppercase tracking-wide text-gray-500 dark:bg-gray-900 dark:text-gray-400">
                            <tr>
                              <th className="px-3 py-2.5">Date</th>
                              <th className="px-3 py-2.5">Check In</th>
                              <th className="px-3 py-2.5">Check Out</th>
                              <th className="px-3 py-2.5">Active Hours</th>
                              <th className="px-3 py-2.5">Focus</th>
                              <th className="px-3 py-2.5">Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredAttendanceDays.map((d) => (
                              <tr
                                key={d.date}
                                className="border-t border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-white/5"
                              >
                                <td className="px-3 py-2 font-medium text-gray-900 dark:text-white">{d.date}</td>
                                <td className="px-3 py-2">{formatClock(d.check_in)}</td>
                                <td className="px-3 py-2">{formatClock(d.check_out)}</td>
                                <td className="px-3 py-2">{d.active_hours_formatted}</td>
                                <td className="px-3 py-2">
                                  {d.focus_score != null ? `${Math.round(d.focus_score)}%` : "—"}
                                </td>
                                <td className="px-3 py-2">
                                  <Badge variant={ATTENDANCE_VARIANT[d.status] ?? "outline"} title={d.week_off_reason ?? undefined}>
                                    {d.status.replace("_", " ")}
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </>
                )}

                {tab === "reports" && (
                  <>
                    {darsQuery.isLoading ? (
                      <div className="flex h-48 items-center justify-center text-gray-400">
                        <Loader2 className="h-6 w-6 animate-spin" />
                      </div>
                    ) : dars.length === 0 ? (
                      <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-gray-400">
                        <FileText className="h-9 w-9" />
                        <p className="text-theme-sm font-medium text-gray-500 dark:text-gray-400">
                          No DAR reports generated yet
                        </p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
                        <div className="lg:col-span-1">
                          <ReportsList reports={dars} selectedDate={selectedDarDate} onSelect={setSelectedDarDate} />
                        </div>
                        <div className="lg:col-span-3">
                          {!selectedDar ? (
                            <div className="flex h-40 flex-col items-center justify-center gap-2 text-center text-theme-sm text-gray-400">
                              <CalendarX className="h-8 w-8" />
                              Select a report from the list.
                            </div>
                          ) : (
                            <>
                              <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-3 dark:border-gray-800">
                                <h2 className="font-semibold text-gray-900 dark:text-white">
                                  {new Date(`${selectedDar.date}T00:00:00`).toLocaleDateString(undefined, {
                                    weekday: "long",
                                    month: "long",
                                    day: "numeric",
                                    year: "numeric",
                                  })}
                                </h2>
                                <Badge
                                  variant={
                                    selectedDar.productivity_score != null && selectedDar.productivity_score >= 70
                                      ? "success"
                                      : selectedDar.productivity_score != null && selectedDar.productivity_score >= 40
                                        ? "warning"
                                        : "destructive"
                                  }
                                >
                                  Score:{" "}
                                  {selectedDar.productivity_score != null
                                    ? `${Math.round(selectedDar.productivity_score)}%`
                                    : "N/A"}
                                </Badge>
                              </div>
                              <DarContent content={selectedDar.content} />
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {isAdmin && currentUser && (
                  <>
                    <FeatureToggles userId={member.user.id} />
                    <AdminControls user={member.user} currentUserId={currentUser.id} onDeleted={() => navigate("/team")} />
                  </>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {selectedShotIndex != null && screenshotsQuery.data && screenshotsQuery.data.length > 0 && (
        <ScreenshotDetailModal
          screenshots={screenshotsQuery.data}
          index={selectedShotIndex}
          showOriginal={showOriginal}
          onShowOriginalChange={setShowOriginal}
          onNavigate={(i) => {
            setSelectedShotIndex(i);
            setShowOriginal(false);
          }}
          onClose={() => setSelectedShotIndex(null)}
        />
      )}
    </>
  );
}
