import type { ActivityLogEntry, ScreenshotEntry } from "@/api";
import { API_BASE_URL } from "@/api";
import { formatClock } from "@/components/Timeline/timeScale";

interface ScreenshotGridProps {
  screenshots: ScreenshotEntry[];
  sessions: ActivityLogEntry[];
  selectedId: number | null;
  onSelect: (screenshot: ScreenshotEntry) => void;
}

// 12.1 — "the app that was active at that time" isn't stored on the
// screenshot row itself; correlate by finding the activity_logs session
// whose time range contains this screenshot's timestamp.
function appActiveAt(sessions: ActivityLogEntry[], timestamp: string): string | null {
  const t = new Date(timestamp).getTime();
  const match = sessions.find((s) => {
    const start = new Date(s.start_time).getTime();
    const end = s.end_time ? new Date(s.end_time).getTime() : start;
    return t >= start && t <= end;
  });
  return match?.app_name ?? null;
}

export default function ScreenshotGrid({ screenshots, sessions, selectedId, onSelect }: ScreenshotGridProps) {
  if (screenshots.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-theme-sm text-gray-400">
        No screenshots captured for this day.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {screenshots.map((shot) => {
        const filename = shot.thumbnail_path?.split(/[\\/]/).pop() ?? shot.file_path.split(/[\\/]/).pop();
        const app = appActiveAt(sessions, shot.timestamp);
        return (
          <button
            key={shot.id}
            onClick={() => onSelect(shot)}
            className={`group overflow-hidden rounded-xl border bg-white text-left transition-all dark:bg-white/[0.03] ${
              selectedId === shot.id
                ? "border-brand-500 ring-2 ring-brand-500/30"
                : "border-gray-200 hover:border-brand-300 dark:border-gray-800"
            }`}
          >
            <div className="aspect-video w-full overflow-hidden bg-gray-100 dark:bg-white/5">
              <img
                src={`${API_BASE_URL}/api/screenshots/file/${filename}`}
                alt={`Screenshot at ${formatClock(shot.timestamp)}`}
                className="h-full w-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
              />
            </div>
            <div className="p-2.5">
              <p className="text-theme-xs font-medium text-gray-700 dark:text-gray-300">
                {formatClock(shot.timestamp)}
              </p>
              <p className="truncate text-theme-xs text-gray-400">{app ?? "Unknown app"}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
