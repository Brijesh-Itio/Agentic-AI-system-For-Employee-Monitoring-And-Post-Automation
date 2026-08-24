import { useEffect, useRef, useState } from "react";
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isAfter,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/shadcn/button";

interface DateSelectorProps {
  date: string; // YYYY-MM-DD
  onChange: (date: string) => void;
}

function shiftDate(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

const todayStr = () => new Date().toISOString().slice(0, 10);
const WEEKDAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"];

export default function DateSelector({ date, onChange }: DateSelectorProps) {
  const isToday_ = date === todayStr();
  const selected = parseISO(date);
  const label = selected.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const [open, setOpen] = useState(false);
  const [viewMonth, setViewMonth] = useState(() => startOfMonth(selected));
  const containerRef = useRef<HTMLDivElement>(null);

  // Re-sync the visible month whenever the popover is (re)opened, so it
  // always starts on the currently-selected date's month rather than
  // wherever it was last left.
  useEffect(() => {
    if (open) setViewMonth(startOfMonth(parseISO(date)));
  }, [open, date]);

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

  const gridStart = startOfWeek(startOfMonth(viewMonth));
  const gridEnd = endOfWeek(endOfMonth(viewMonth));
  const days = eachDayOfInterval({ start: gridStart, end: gridEnd });
  const today = new Date();

  const pick = (d: Date) => {
    if (isAfter(d, today) && !isSameDay(d, today)) return; // future dates stay disabled
    onChange(format(d, "yyyy-MM-dd"));
    setOpen(false);
  };

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="icon" onClick={() => onChange(shiftDate(date, -1))} aria-label="Previous day">
        <ChevronLeft className="h-4 w-4" />
      </Button>

      <div ref={containerRef} className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-haspopup="dialog"
          aria-expanded={open}
          className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-brand-300 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-white/5"
        >
          <Calendar className="h-4 w-4 text-gray-400" />
          {label}
        </button>

        {open && (
          <div
            role="dialog"
            aria-label="Choose date"
            className="absolute left-0 top-[calc(100%+8px)] z-50 w-72 rounded-xl border border-gray-200 bg-white p-3 shadow-xl shadow-gray-900/10 dark:border-gray-700 dark:bg-gray-900 dark:shadow-black/30"
          >
            <div className="mb-2 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setViewMonth((m) => subMonths(m, 1))}
                className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
                aria-label="Previous month"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm font-semibold text-gray-900 dark:text-white">{format(viewMonth, "MMMM yyyy")}</span>
              <button
                type="button"
                onClick={() => setViewMonth((m) => addMonths(m, 1))}
                disabled={isSameMonth(viewMonth, today)}
                className="flex h-7 w-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-30 dark:text-gray-400 dark:hover:bg-white/10"
                aria-label="Next month"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <div className="mb-1 grid grid-cols-7 gap-1 text-center text-theme-xs font-medium text-gray-400">
              {WEEKDAY_LABELS.map((w, i) => (
                <span key={i}>{w}</span>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
              {days.map((d) => {
                const disabled = isAfter(d, today) && !isSameDay(d, today);
                const outOfMonth = !isSameMonth(d, viewMonth);
                const isSelected = isSameDay(d, selected);
                const isTodayDate = isToday(d);
                return (
                  <button
                    key={d.toISOString()}
                    type="button"
                    onClick={() => pick(d)}
                    disabled={disabled}
                    className={`flex h-8 w-8 items-center justify-center rounded-lg text-theme-xs transition-colors ${
                      isSelected
                        ? "bg-brand-500 font-semibold text-white"
                        : disabled
                          ? "cursor-not-allowed text-gray-300 dark:text-gray-700"
                          : outOfMonth
                            ? "text-gray-300 hover:bg-gray-50 dark:text-gray-600 dark:hover:bg-white/5"
                            : "text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-white/10"
                    } ${isTodayDate && !isSelected ? "ring-1 ring-inset ring-brand-400" : ""}`}
                  >
                    {format(d, "d")}
                  </button>
                );
              })}
            </div>

            {!isToday_ && (
              <button
                type="button"
                onClick={() => {
                  onChange(todayStr());
                  setOpen(false);
                }}
                className="mt-2 w-full rounded-lg py-1.5 text-center text-theme-xs font-medium text-brand-500 hover:bg-brand-50 dark:hover:bg-brand-500/10"
              >
                Jump to today
              </button>
            )}
          </div>
        )}
      </div>

      <Button
        variant="outline"
        size="icon"
        onClick={() => onChange(shiftDate(date, 1))}
        disabled={isToday_}
        aria-label="Next day"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>

      {!isToday_ && (
        <Button variant="secondary" size="sm" onClick={() => onChange(todayStr())}>
          Today
        </Button>
      )}
    </div>
  );
}
