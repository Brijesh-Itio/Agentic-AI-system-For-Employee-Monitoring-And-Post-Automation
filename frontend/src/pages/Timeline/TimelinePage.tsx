import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import DateSelector from "@/components/Timeline/DateSelector";
import TimelineTrack from "@/components/Timeline/TimelineTrack";
import ContextSwitchingStrip from "@/components/Timeline/ContextSwitchingStrip";
import SessionDetailPanel from "@/components/Timeline/SessionDetailPanel";
import ScreenshotModal from "@/components/Timeline/ScreenshotModal";
import { computeDayBounds, CATEGORY_COLOR, CATEGORY_LABEL } from "@/components/Timeline/timeScale";
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

export default function TimelinePage() {
  const [date, setDate] = useState(todayStr());
  const [selectedSession, setSelectedSession] = useState<ActivityLogEntry | null>(null);
  const [selectedScreenshot, setSelectedScreenshot] = useState<ScreenshotEntry | null>(null);

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
  const categories: Category[] = ["productive", "neutral", "distraction", "uncategorised"];

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

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>Activity</CardTitle>
            <div className="flex items-center gap-3">
              {categories.map((c) => (
                <span key={c} className="flex items-center gap-1.5 text-theme-xs text-gray-500 dark:text-gray-400">
                  <span className={`h-2.5 w-2.5 rounded-full ${CATEGORY_COLOR[c]}`} />
                  {CATEGORY_LABEL[c]}
                </span>
              ))}
            </div>
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
