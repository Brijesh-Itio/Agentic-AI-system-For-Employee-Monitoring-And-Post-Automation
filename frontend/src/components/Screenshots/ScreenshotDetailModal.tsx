import { useEffect } from "react";
import { ChevronLeft, ChevronRight, Eye, EyeOff, X } from "lucide-react";
import type { ScreenshotEntry } from "@/api";
import { API_BASE_URL } from "@/api";
import { formatClock } from "@/components/Timeline/timeScale";
import { Button } from "@/components/shadcn/button";

interface ScreenshotDetailModalProps {
  screenshots: ScreenshotEntry[];
  index: number;
  showOriginal: boolean;
  onShowOriginalChange: (value: boolean) => void;
  onNavigate: (index: number) => void;
  onClose: () => void;
}

export default function ScreenshotDetailModal({
  screenshots,
  index,
  showOriginal,
  onShowOriginalChange,
  onNavigate,
  onClose,
}: ScreenshotDetailModalProps) {
  const shot = screenshots[index];

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && index > 0) onNavigate(index - 1);
      if (e.key === "ArrowRight" && index < screenshots.length - 1) onNavigate(index + 1);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [index, screenshots.length, onNavigate, onClose]);

  if (!shot) return null;

  // 12.4 — blur toggle: fall back to the blurred file if no unblurred
  // original was captured (BLUR_SCREENSHOTS was off, so file_path IS the
  // only version — nothing to toggle to).
  const activePath =
    showOriginal && shot.original_path ? shot.original_path : shot.file_path;
  const filename = activePath.split(/[\\/]/).pop();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6" onClick={onClose}>
      <button
        onClick={onClose}
        className="absolute right-5 top-5 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
      >
        <X className="h-5 w-5" />
      </button>

      {index > 0 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNavigate(index - 1); }}
          className="absolute left-5 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>
      )}
      {index < screenshots.length - 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNavigate(index + 1); }}
          className="absolute right-5 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      )}

      <div
        className="max-h-full max-w-4xl overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-gray-900"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={`${API_BASE_URL}/api/screenshots/file/${filename}`}
          alt="Screenshot"
          className="max-h-[75vh] w-full object-contain"
        />
        <div className="flex items-center justify-between px-4 py-3">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {formatClock(shot.timestamp)} · {index + 1} of {screenshots.length}
          </div>
          {shot.original_path && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onShowOriginalChange(!showOriginal)}
            >
              {showOriginal ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              {showOriginal ? "Show Blurred" : "Show Original"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
