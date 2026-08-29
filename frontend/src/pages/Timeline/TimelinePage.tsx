import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { Loader2 } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import DateSelector from "@/components/Timeline/DateSelector";
import TimelineTrack from "@/components/Timeline/TimelineTrack";
import TimelineSummaryStats from "@/components/Timeline/TimelineSummaryStats";
import CategoryLegend from "@/components/Timeline/CategoryLegend";
import ContextSwitchingStrip from "@/components/Timeline/ContextSwitchingStrip";
import SessionDetailPanel from "@/components/Timeline/SessionDetailPanel";
import ScreenshotModal from "@/components/Timeline/ScreenshotModal";
import { computeDayBounds } from "@/components/Timeline/timeScale";
import {
  getActivityByDate,
  getIdlePeriodsByDate,
  getContextSwitchingByDate,
  getScreenshotsByDate,
  type ActivityLogEntry,
  type ScreenshotEntry,
  type Category,
} from "@/api";

const todayStr = () => new Date().toISOString().slice(0, 10);
const shiftDate = (date: string, days: number) => {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

export default function TimelinePage() {
  // Supports deep links like /timeline?date=2026-08-05 (e.g. from the
  // Attendance page's day drawer) — falls back to today for a bare visit
  // or a malformed value, so the default flow is unaffected.
  const [searchParams] = useSearchParams();
  const [date, setDate] = useState(() => {
    const requested = searchParams.get("date");
    return requested && /^\d{4}-\d{2}-\d{2}$/.test(requested) ? requested : todayStr();
  });
  const [selectedSession, setSelectedSession] = useState<ActivityLogEntry | null>(null);
  const [selectedScreenshot, setSelectedScreenshot] = useState<ScreenshotEntry | null>(null);
  const [activeCategory, setActiveCategory] = useState<Category | null>(null);

  // Left/right arrow keys step a day at a time, mirroring the chevron
  // buttons — skipped while a modal is open or a screenshot cluster is
  // focused, so it never fights with a picker's own keyboard handling.
  useEffect(() => {
    if (selectedSession || selectedScreenshot) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) return;
      if (e.key === "ArrowLeft") setDate((d) => shiftDate(d, -1));
      if (e.key === "ArrowRight" && date !== todayStr()) setDate((d) => shiftDate(d, 1));
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [selectedSession, selectedScreenshot, date]);

  const sessionsQuery = useQuery({
    queryKey: ["activity", "date", date],
    queryFn: () => getActivityByDate(date),
  });
  const idleQuery = useQuery({
    queryKey: ["idle", "date", date],
    queryFn: () => getIdlePeriodsByDate(date),
  });
  const switchingQuery = useQuery({
    queryKey: ["context-switching", "date", date],
    queryFn: () => getContextSwitchingByDate(date),
  });
  const screenshotsQuery = useQuery({
    queryKey: ["screenshots", "date", date],
    queryFn: () => getScreenshotsByDate(date),
  });

  const sessions = sessionsQuery.data ?? [];
  const idlePeriods = idleQuery.data ?? [];
  const switching = switchingQuery.data ?? [];
  const screenshots = screenshotsQuery.data ?? [];

  const bounds = useMemo(() => computeDayBounds(date, sessions, idlePeriods), [date, sessions, idlePeriods]);

  const nearbyScreenshot = useMemo(() => {
    if (!selectedSession) return null;
    const start = new Date(selectedSession.start_time).getTime();
    const end = selectedSession.end_time ? new Date(selectedSession.end_time).getTime() : start;
    return (
      screenshots.find((s) => {
        const t = new Date(s.timestamp).getTime();
        return t >= start - 5 * 60_000 && t <= end + 5 * 60_000;
      }) ?? null
    );
  }, [selectedSession, screenshots]);

  const isLoading = sessionsQuery.isLoading || idleQuery.isLoading;

  return (
    <>
      <PageMeta title="Timeline | WorkPulse AI" description="Minute-by-minute view of your work day." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Timeline</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Every app session for the selected day, colour-coded by category.
            </p>
          </div>
          <DateSelector date={date} onChange={setDate} />
        </div>

        <TimelineSummaryStats
          sessions={sessions}
          switching={switching}
          loading={sessionsQuery.isLoading || switchingQuery.isLoading}
        />

        <Card>
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
            <CardTitle>Activity</CardTitle>
            <CategoryLegend
              active={activeCategory}
              onToggle={(c) => setActiveCategory((prev) => (prev === c ? null : c))}
            />
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            {isLoading ? (
              <div className="flex h-24 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="flex h-24 items-center justify-center text-theme-sm text-gray-400">
                No activity tracked for this day.
              </div>
            ) : (
              <TimelineTrack
                bounds={bounds}
                sessions={sessions}
                idlePeriods={idlePeriods}
                screenshots={screenshots}
                selectedSessionId={selectedSession?.id ?? null}
                activeCategory={activeCategory}
                showNowLine={date === todayStr()}
                onSelectSession={setSelectedSession}
                onSelectScreenshot={setSelectedScreenshot}
              />
            )}

            <ContextSwitchingStrip hours={switching} startHour={bounds.start.getHours()} endHour={bounds.end.getHours()} />
          </CardContent>
        </Card>
      </div>

      {selectedSession && (
        <SessionDetailPanel
          session={selectedSession}
          nearbyScreenshot={nearbyScreenshot}
          onClose={() => setSelectedSession(null)}
        />
      )}

      {selectedScreenshot && (
        <ScreenshotModal screenshot={selectedScreenshot} onClose={() => setSelectedScreenshot(null)} />
      )}
    </>
  );
}
