import { useState } from "react";
import type { ActivityLogEntry, Category, IdlePeriod } from "@/api";
import {
  type DayBounds,
  CATEGORY_COLOR,
  CATEGORY_LABEL,
  formatClock,
  formatDuration,
  hourMarks,
  percentPosition,
  percentWidth,
} from "./timeScale";

interface TimelineTrackProps {
  bounds: DayBounds;
  sessions: ActivityLogEntry[];
  idlePeriods: IdlePeriod[];
  selectedSessionId: number | null;
  activeCategory?: Category | null;
  showNowLine?: boolean;
  onSelectSession: (session: ActivityLogEntry) => void;
}

export default function TimelineTrack({
  bounds,
  sessions,
  idlePeriods,
  selectedSessionId,
  activeCategory = null,
  showNowLine = false,
  onSelectSession,
}: TimelineTrackProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  const marks = hourMarks(bounds);
  const now = new Date();
  const nowPosition =
    showNowLine && now >= bounds.start && now <= bounds.end ? percentPosition(bounds, now) : null;

  return (
    <div className="relative">
      {/* Hour ruler — gridlines every hour, labels every other hour to
          stay legible regardless of how wide the visible window is. */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-32">
        {marks.map((mark) => (
          <div
            key={mark.hour}
            className="absolute top-0 h-full w-px bg-gray-200/70 dark:bg-white/[0.06]"
            style={{ left: `${mark.position}%` }}
          />
        ))}
      </div>

      <div className="relative h-32 w-full overflow-visible rounded-xl bg-gray-50 dark:bg-white/[0.03]">
        {/* Idle period markers — grey hatched sections */}
        {idlePeriods.map((idle) => {
          const left = percentPosition(bounds, new Date(idle.start_time));
          const width = idle.end_time
            ? percentWidth(bounds, new Date(idle.start_time), new Date(idle.end_time))
            : 0.3;
          return (
            <div
              key={`idle-${idle.id}`}
              className="group absolute top-8 h-16 rounded-sm"
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

        {/* Session bars, colour-coded by category */}
        {sessions.map((session) => {
          const start = new Date(session.start_time);
          const end = session.end_time ? new Date(session.end_time) : start;
          const left = percentPosition(bounds, start);
          const width = percentWidth(bounds, start, end);
          const isSelected = selectedSessionId === session.id;
          const isDimmed = activeCategory !== null && activeCategory !== session.category;

          return (
            <div
              key={session.id}
              className="absolute top-8 h-16 transition-opacity"
              style={{ left: `${left}%`, width: `${width}%`, opacity: isDimmed ? 0.25 : 1 }}
            >
              <button
                onClick={() => onSelectSession(session)}
                onMouseEnter={() => setHoveredId(session.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={`h-full w-full overflow-hidden rounded-md text-left shadow-sm transition-all ${CATEGORY_COLOR[session.category]} ${
                  isSelected ? "ring-2 ring-offset-1 ring-brand-500" : "hover:brightness-110 hover:shadow-md"
                }`}
              >
                {width > 4 && (
                  <span className="block truncate px-1.5 py-1 text-[11px] font-medium text-white/95">
                    {session.app_name}
                  </span>
                )}
              </button>

              {/* Tooltip on hover */}
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

        {/* "Now" indicator — only meaningful while viewing today */}
        {nowPosition !== null && (
          <div className="pointer-events-none absolute top-0 z-10 h-full" style={{ left: `${nowPosition}%` }}>
            <div className="h-full w-0.5 bg-error-500" />
            <span className="absolute -top-5 -translate-x-1/2 rounded bg-error-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
              Now
            </span>
          </div>
        )}
      </div>

      {/* Hour labels beneath the track, every other hour to avoid crowding */}
      <div className="relative mt-1.5 h-4">
        {marks
          .filter((m) => m.hour % 2 === 0)
          .map((mark) => (
            <span
              key={mark.hour}
              className="absolute -translate-x-1/2 text-[10px] text-gray-400 dark:text-gray-500"
              style={{ left: `${mark.position}%` }}
            >
              {mark.label}
            </span>
          ))}
      </div>
    </div>
  );
}
