import { X } from "lucide-react";
import type { ActivityLogEntry, ScreenshotEntry } from "@/api";
import { CATEGORY_COLOR, CATEGORY_LABEL, formatClock, formatDuration } from "./timeScale";
import { API_BASE_URL } from "@/api";

interface SessionDetailPanelProps {
  session: ActivityLogEntry;
  nearbyScreenshot: ScreenshotEntry | null;
  onClose: () => void;
}

export default function SessionDetailPanel({ session, nearbyScreenshot, onClose }: SessionDetailPanelProps) {
  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-sm border-l border-gray-200 bg-white p-5 shadow-2xl dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">{session.app_name}</h3>
          <span
            className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${CATEGORY_COLOR[session.category]}`}
          >
            {CATEGORY_LABEL[session.category]}
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-white/5"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5 space-y-4 text-sm">
        <div>
          <p className="text-theme-xs font-medium uppercase text-gray-400">Window title</p>
          <p className="mt-1 text-gray-700 dark:text-gray-300">
            {session.window_title || "—"}
          </p>
          <p className="mt-1 text-theme-xs text-gray-400">
            Only the most recent window title is recorded per session — full title history isn't
            tracked yet.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-theme-xs font-medium uppercase text-gray-400">Start</p>
            <p className="mt-1 text-gray-700 dark:text-gray-300">{formatClock(session.start_time)}</p>
          </div>
          <div>
            <p className="text-theme-xs font-medium uppercase text-gray-400">End</p>
            <p className="mt-1 text-gray-700 dark:text-gray-300">
              {session.end_time ? formatClock(session.end_time) : "—"}
            </p>
          </div>
        </div>

        <div>
          <p className="text-theme-xs font-medium uppercase text-gray-400">Duration</p>
          <p className="mt-1 text-gray-700 dark:text-gray-300">{formatDuration(session.duration_seconds)}</p>
        </div>

        {nearbyScreenshot && (
          <div>
            <p className="text-theme-xs font-medium uppercase text-gray-400">Nearby screenshot</p>
            <img
              src={`${API_BASE_URL}/api/screenshots/file/${nearbyScreenshot.thumbnail_path?.split(/[\\/]/).pop()}`}
              alt="Screenshot near this session"
              className="mt-2 w-full rounded-lg border border-gray-200 dark:border-gray-700"
            />
          </div>
        )}
      </div>
    </div>
  );
}
