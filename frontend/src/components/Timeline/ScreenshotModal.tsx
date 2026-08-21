import { X } from "lucide-react";
import type { ScreenshotEntry } from "@/api";
import { API_BASE_URL } from "@/api";
import { formatClock } from "./timeScale";

interface ScreenshotModalProps {
  screenshot: ScreenshotEntry;
  onClose: () => void;
}

export default function ScreenshotModal({ screenshot, onClose }: ScreenshotModalProps) {
  const filename = screenshot.file_path.split(/[\\/]/).pop();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
      onClick={onClose}
    >
      <div
        className="relative max-h-full max-w-3xl overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-gray-900"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute right-3 top-3 z-10 rounded-full bg-black/50 p-1.5 text-white hover:bg-black/70"
        >
          <X className="h-4 w-4" />
        </button>
        <img src={`${API_BASE_URL}/api/screenshots/file/${filename}`} alt="Screenshot" className="max-h-[80vh] w-full object-contain" />
        <div className="flex items-center justify-between px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
          <span>{formatClock(screenshot.timestamp)}</span>
          {screenshot.is_blurred && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs dark:bg-white/5">Blurred</span>
          )}
        </div>
      </div>
    </div>
  );
}
