import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, ImageOff, Loader2, X } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import DateSelector from "@/components/Timeline/DateSelector";
import TimelineTrack from "@/components/Timeline/TimelineTrack";
import ScreenshotGrid from "@/components/Screenshots/ScreenshotGrid";
import ScreenshotDetailModal from "@/components/Screenshots/ScreenshotDetailModal";
import { computeDayBounds } from "@/components/Timeline/timeScale";
import { getScreenshotsByDate, getActivityByDate, getIdlePeriodsByDate, type ScreenshotEntry } from "@/api";

const todayStr = () => new Date().toISOString().slice(0, 10);

// "HH:MM" from a screenshot's timestamp, for comparing against the
// <input type="time"> filter values — both are plain 24h clock strings.
function clockValue(timestamp: string): string {
  return new Date(timestamp).toTimeString().slice(0, 5);
}

export default function ScreenshotsPage() {
  const [date, setDate] = useState(todayStr());
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [timeFrom, setTimeFrom] = useState("");
  const [timeTo, setTimeTo] = useState("");

  const screenshotsQuery = useQuery({
    queryKey: ["screenshots", "date", date],
    queryFn: () => getScreenshotsByDate(date),
  });
  const sessionsQuery = useQuery({
    queryKey: ["activity", "date", date],
    queryFn: () => getActivityByDate(date),
  });
  const idleQuery = useQuery({
    queryKey: ["idle", "date", date],
    queryFn: () => getIdlePeriodsByDate(date),
  });

  const screenshots = screenshotsQuery.data ?? [];
  const sessions = sessionsQuery.data ?? [];
  const idlePeriods = idleQuery.data ?? [];

  // A new day invalidates whatever time range we'd narrowed down to.
  useEffect(() => {
    setTimeFrom("");
    setTimeTo("");
  }, [date]);

  // Changing the time range can shift or invalidate whichever index the
  // detail modal had open, since it always indexes into the filtered list.
  useEffect(() => setSelectedIndex(null), [timeFrom, timeTo]);

  const hasActiveFilter = timeFrom !== "" || timeTo !== "";
  const filteredScreenshots = useMemo(() => {
    if (!hasActiveFilter) return screenshots;
    return screenshots.filter((s) => {
      const clock = clockValue(s.timestamp);
      if (timeFrom && clock < timeFrom) return false;
      if (timeTo && clock > timeTo) return false;
      return true;
    });
  }, [screenshots, timeFrom, timeTo, hasActiveFilter]);

  const bounds = useMemo(() => computeDayBounds(date, sessions, idlePeriods), [date, sessions, idlePeriods]);

  const selectedScreenshot: ScreenshotEntry | null =
    selectedIndex != null ? filteredScreenshots[selectedIndex] ?? null : null;

  const handleSelect = (shot: ScreenshotEntry) => {
    const idx = filteredScreenshots.findIndex((s) => s.id === shot.id);
    setShowOriginal(false);
    setSelectedIndex(idx);
  };

  const clearTimeFilter = () => {
    setTimeFrom("");
    setTimeTo("");
  };

  return (
    <>
      <PageMeta title="Screenshots | WorkPulse AI" description="Browse every captured screenshot in a searchable gallery." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Screenshots</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Every screenshot captured on the selected day, correlated with your activity.
            </p>
          </div>
          <DateSelector date={date} onChange={setDate} />
        </div>

        {/* 12.5 timeline correlation strip */}
        {screenshots.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-gray-500 dark:text-gray-400">Activity Timeline</CardTitle>
            </CardHeader>
            <CardContent className="pt-1">
              <TimelineTrack
                bounds={bounds}
                sessions={sessions}
                idlePeriods={idlePeriods}
                screenshots={filteredScreenshots}
                selectedSessionId={null}
                selectedScreenshotId={selectedScreenshot?.id ?? null}
                onSelectSession={() => {}}
                onSelectScreenshot={handleSelect}
              />
            </CardContent>
          </Card>
        )}

        {screenshots.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
            <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Time range</span>
              <input
                type="time"
                value={timeFrom}
                onChange={(e) => setTimeFrom(e.target.value)}
                className="rounded-lg border border-gray-200 bg-gray-50 px-2 py-1.5 text-xs text-gray-700 focus:border-brand-400 focus:bg-white focus:outline-none dark:border-gray-700 dark:bg-white/5 dark:text-gray-200"
              />
              <span>–</span>
              <input
                type="time"
                value={timeTo}
                onChange={(e) => setTimeTo(e.target.value)}
                className="rounded-lg border border-gray-200 bg-gray-50 px-2 py-1.5 text-xs text-gray-700 focus:border-brand-400 focus:bg-white focus:outline-none dark:border-gray-700 dark:bg-white/5 dark:text-gray-200"
              />
            </div>

            {hasActiveFilter && (
              <button
                onClick={clearTimeFilter}
                className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-white/10 dark:hover:text-gray-200"
              >
                <X className="h-3 w-3" />
                Clear
              </button>
            )}

            <span className="ml-auto text-xs text-gray-400">
              {hasActiveFilter
                ? `${filteredScreenshots.length} of ${screenshots.length} screenshots`
                : `${screenshots.length} ${screenshots.length === 1 ? "screenshot" : "screenshots"}`}
            </span>
          </div>
        )}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Gallery</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {screenshotsQuery.isLoading ? (
              <div className="flex h-48 items-center justify-center text-gray-400">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : screenshots.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-gray-400">
                <ImageOff className="h-9 w-9" />
                <p className="text-theme-sm font-medium text-gray-500 dark:text-gray-400">
                  No screenshots captured for this day
                </p>
                <p className="text-theme-xs text-gray-400 dark:text-gray-500">
                  The desktop agent captures these automatically while it's running.
                </p>
              </div>
            ) : filteredScreenshots.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-gray-400">
                <Clock className="h-9 w-9" />
                <p className="text-theme-sm font-medium text-gray-500 dark:text-gray-400">
                  No screenshots in this time range
                </p>
                <button onClick={clearTimeFilter} className="text-theme-xs text-brand-500 hover:underline">
                  Clear time filter
                </button>
              </div>
            ) : (
              <ScreenshotGrid
                screenshots={filteredScreenshots}
                sessions={sessions}
                selectedId={selectedScreenshot?.id ?? null}
                onSelect={handleSelect}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {selectedIndex != null && filteredScreenshots.length > 0 && (
        <ScreenshotDetailModal
          screenshots={filteredScreenshots}
          index={selectedIndex}
          showOriginal={showOriginal}
          onShowOriginalChange={setShowOriginal}
          onNavigate={(i) => { setSelectedIndex(i); setShowOriginal(false); }}
          onClose={() => setSelectedIndex(null)}
        />
      )}
    </>
  );
}
