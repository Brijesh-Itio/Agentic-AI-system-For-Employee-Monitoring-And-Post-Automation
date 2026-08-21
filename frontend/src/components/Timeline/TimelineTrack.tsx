import { useState } from "react";
import { Camera } from "lucide-react";
import type { ActivityLogEntry, IdlePeriod, ScreenshotEntry } from "@/api";
import {
  type DayBounds,
  CATEGORY_COLOR,
  CATEGORY_LABEL,
  formatClock,
  formatDuration,
  percentPosition,
  percentWidth,
} from "./timeScale";

interface TimelineTrackProps {
  bounds: DayBounds;
  sessions: ActivityLogEntry[];
  idlePeriods: IdlePeriod[];
  screenshots: ScreenshotEntry[];
  selectedSessionId: number | null;
  selectedScreenshotId?: number | null;
  onSelectSession: (session: ActivityLogEntry) => void;
  onSelectScreenshot: (screenshot: ScreenshotEntry) => void;
}

export default function TimelineTrack({
  bounds,
  sessions,
  idlePeriods,
  screenshots,
  selectedSessionId,
  selectedScreenshotId = null,
  onSelectSession,
  onSelectScreenshot,
}: TimelineTrackProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  return (
    <div className="relative h-24 w-full rounded-xl bg-gray-50 dark:bg-white/[0.03]">
      {/* 10.6 idle period markers — grey hatched sections */}
      {idlePeriods.map((idle) => {
        const left = percentPosition(bounds, new Date(idle.start_time));
        const width = idle.end_time
          ? percentWidth(bounds, new Date(idle.start_time), new Date(idle.end_time))
          : 0.3;
        return (
          <div
            key={`idle-${idle.id}`}
            className="group absolute top-3 h-14 rounded-sm"
            style={{
              left: `${left}%`,
              width: `${width}%`,
              backgroundImage:
                "repeating-linear-gradient(45deg, rgba(148,163,184,0.35) 0, rgba(148,163,184,0.35) 4px, transparent 4px, transparent 8px)",
            }}
            title={`Idle for ${formatDuration(idle.duration_seconds)}`}
          />
        );
      })}

      {/* 10.2 session bars, colour-coded by category */}
      {sessions.map((session) => {
        const start = new Date(session.start_time);
        const end = session.end_time ? new Date(session.end_time) : start;
        const left = percentPosition(bounds, start);
        const width = percentWidth(bounds, start, end);
        const isSelected = selectedSessionId === session.id;

        return (
          <div key={session.id} className="absolute top-3 h-14" style={{ left: `${left}%`, width: `${width}%` }}>
            <button
              onClick={() => onSelectSession(session)}
              onMouseEnter={() => setHoveredId(session.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={`h-full w-full overflow-hidden rounded-md text-left transition-all ${CATEGORY_COLOR[session.category]} ${
                isSelected ? "ring-2 ring-offset-1 ring-brand-500" : "hover:brightness-110"
              }`}
            >
              {width > 4 && (
                <span className="block truncate px-1.5 py-1 text-[11px] font-medium text-white/95">
                  {session.app_name}
                </span>
              )}
            </button>

            {/* 10.3 tooltip on hover */}
            {hoveredId === session.id && (
              <div className="absolute bottom-full left-1/2 z-20 mb-2 w-56 -translate-x-1/2 rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <p className="font-semibold text-gray-900 dark:text-white">{session.app_name}</p>
                {session.window_title && (
                  <p className="mt-0.5 truncate text-gray-500 dark:text-gray-400">{session.window_title}</p>
                )}
                <div className="mt-2 flex items-center justify-between text-gray-500 dark:text-gray-400">
                  <span>
                    {formatClock(session.start_time)}
                    {session.end_time ? ` – ${formatClock(session.end_time)}` : ""}
                  </span>
                  <span>{formatDuration(session.duration_seconds)}</span>
                </div>
                <span
                  className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-medium text-white ${CATEGORY_COLOR[session.category]}`}
                >
                  {CATEGORY_LABEL[session.category]}
                </span>
              </div>
            )}
          </div>
        );
      })}

      {/* 10.5 screenshot markers */}
      {screenshots.map((shot) => {
        const left = percentPosition(bounds, new Date(shot.timestamp));
        return (
          <button
            key={`shot-${shot.id}`}
            onClick={() => onSelectScreenshot(shot)}
            className={`absolute top-0 flex h-5 w-5 -translate-x-1/2 items-center justify-center rounded-full border text-white shadow-sm hover:scale-110 ${
              selectedScreenshotId === shot.id
                ? "border-white bg-warning-500 scale-125 ring-2 ring-warning-300 dark:border-gray-900"
                : "border-white bg-brand-500 dark:border-gray-900"
            }`}
            style={{ left: `${left}%` }}
            title={`Screenshot at ${formatClock(shot.timestamp)}`}
          >
            <Camera className="h-3 w-3" />
          </button>
        );
      })}
    </div>
  );
}
