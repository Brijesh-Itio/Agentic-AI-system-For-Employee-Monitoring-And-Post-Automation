import { useEffect, useRef, useState } from "react";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";

interface MonthPickerProps {
  month: string; // YYYY-MM
  onChange: (month: string) => void;
  maxMonth: string; // YYYY-MM — can't navigate past this (the current month)
}

const MONTH_LABELS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function monthLabel(month: string): string {
  const [year, mon] = month.split("-").map(Number);
  return new Date(year, mon - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

export default function MonthPicker({ month, onChange, maxMonth }: MonthPickerProps) {
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(() => Number(month.split("-")[0]));
  const containerRef = useRef<HTMLDivElement>(null);

  const [selectedYear, selectedMonthNum] = month.split("-").map(Number);
  const [maxYear, maxMonthNum] = maxMonth.split("-").map(Number);

  useEffect(() => {
    if (open) setViewYear(selectedYear);
  }, [open, selectedYear]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    const handleEscape = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const pick = (monthNum: number) => {
    const candidate = `${viewYear}-${String(monthNum).padStart(2, "0")}`;
    if (candidate > maxMonth) return;
    onChange(candidate);
    setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-brand-300 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-white/5"
      >
        <Calendar className="h-4 w-4 text-gray-400" />
        {monthLabel(month)}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Choose month"
          className="absolute left-1/2 top-[calc(100%+8px)] z-50 w-56 -translate-x-1/2 rounded-xl border border-gray-200 bg-white p-3 shadow-xl shadow-gray-900/10 dark:border-gray-700 dark:bg-gray-900 dark:shadow-black/30"
        >
          <div className="mb-2 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setViewYear((y) => y - 1)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
              aria-label="Previous year"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">{viewYear}</span>
            <button
              type="button"
              onClick={() => setViewYear((y) => y + 1)}
              disabled={viewYear >= maxYear}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-30 dark:text-gray-400 dark:hover:bg-white/10"
              aria-label="Next year"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-3 gap-1.5">
            {MONTH_LABELS.map((label, idx) => {
              const monthNum = idx + 1;
              const disabled = viewYear === maxYear && monthNum > maxMonthNum;
              const isSelected = viewYear === selectedYear && monthNum === selectedMonthNum;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => pick(monthNum)}
                  disabled={disabled}
                  className={`rounded-lg py-1.5 text-theme-xs transition-colors ${
                    isSelected
                      ? "bg-brand-500 font-semibold text-white"
                      : disabled
                        ? "cursor-not-allowed text-gray-300 dark:text-gray-700"
                        : "text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-white/10"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
