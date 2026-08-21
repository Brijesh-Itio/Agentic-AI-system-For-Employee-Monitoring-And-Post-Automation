import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Loader2 } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import DateSelector from "@/components/Timeline/DateSelector";
import TimelineTrack from "@/components/Timeline/TimelineTrack";
import ScreenshotGrid from "@/components/Screenshots/ScreenshotGrid";
import ScreenshotDetailModal from "@/components/Screenshots/ScreenshotDetailModal";
import { computeDayBounds } from "@/components/Timeline/timeScale";
import {
  getScreenshotsByDate,
  getActivityByDate,
  getIdlePeriodsByDate,
  captureScreenshotNow,
  type ScreenshotEntry,
} from "@/api";

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function ScreenshotsPage() {
  const [date, setDate] = useState(todayStr());
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const queryClient = useQueryClient();

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

  const captureMutation = useMutation({
    mutationFn: captureScreenshotNow,
    onSuccess: () => {
      if (date === todayStr()) {
        queryClient.invalidateQueries({ queryKey: ["screenshots", "date", date] });
      }
    },
  });

  const screenshots = screenshotsQuery.data ?? [];
  const sessions = sessionsQuery.data ?? [];
  const idlePeriods = idleQuery.data ?? [];

  const bounds = useMemo(() => computeDayBounds(date, sessions, idlePeriods), [date, sessions, idlePeriods]);

  const selectedScreenshot: ScreenshotEntry | null =
    selectedIndex != null ? screenshots[selectedIndex] ?? null : null;

  const handleSelect = (shot: ScreenshotEntry) => {
    const idx = screenshots.findIndex((s) => s.id === shot.id);
    setShowOriginal(false);
    setSelectedIndex(idx);
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
          <div className="flex items-center gap-3">
            <DateSelector date={date} onChange={setDate} />
            <Button onClick={() => captureMutation.mutate()} disabled={captureMutation.isPending}>
              {captureMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              Capture Now
            </Button>
          </div>
        </div>

        {/* 12.5 timeline correlation strip */}
        {screenshots.length > 0 && (
          <Card>
            <CardContent className="pt-5">
              <TimelineTrack
                bounds={bounds}
                sessions={sessions}
                idlePeriods={idlePeriods}
                screenshots={screenshots}
                selectedSessionId={null}
                selectedScreenshotId={selectedScreenshot?.id ?? null}
                onSelectSession={() => {}}
                onSelectScreenshot={handleSelect}
              />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Gallery</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {screenshotsQuery.isLoading ? (
              <div className="flex h-40 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              <ScreenshotGrid
                screenshots={screenshots}
                sessions={sessions}
                selectedId={selectedScreenshot?.id ?? null}
                onSelect={handleSelect}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {selectedIndex != null && screenshots.length > 0 && (
        <ScreenshotDetailModal
          screenshots={screenshots}
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
