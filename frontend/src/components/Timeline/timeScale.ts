import type { ActivityLogEntry, Category, IdlePeriod } from "@/api";

// Default visible window when there's no data to derive bounds from.
const DEFAULT_START_HOUR = 6;
const DEFAULT_END_HOUR = 23;

export interface DayBounds {
  start: Date;
  end: Date;
  totalMs: number;
}

export function computeDayBounds(
  day: string,
  sessions: ActivityLogEntry[],
  idlePeriods: IdlePeriod[]
): DayBounds {
  const dayStart = new Date(`${day}T00:00:00`);
  let earliest = new Date(`${day}T${String(DEFAULT_START_HOUR).padStart(2, "0")}:00:00`);
  let latest = new Date(`${day}T${String(DEFAULT_END_HOUR).padStart(2, "0")}:00:00`);

  const allTimestamps: Date[] = [];
  for (const s of sessions) {
    allTimestamps.push(new Date(s.start_time));
    if (s.end_time) allTimestamps.push(new Date(s.end_time));
  }
  for (const idle of idlePeriods) {
    allTimestamps.push(new Date(idle.start_time));
    if (idle.end_time) allTimestamps.push(new Date(idle.end_time));
  }

  for (const t of allTimestamps) {
    if (t < earliest) earliest = t;
    if (t > latest) latest = t;
  }

  // Small padding so the first/last session isn't flush against the edge.
  const paddingMs = 15 * 60 * 1000;
  const start = new Date(Math.max(dayStart.getTime(), earliest.getTime() - paddingMs));
  const end = new Date(latest.getTime() + paddingMs);

  return { start, end, totalMs: end.getTime() - start.getTime() };
}

export function percentPosition(bounds: DayBounds, at: Date): number {
  if (bounds.totalMs <= 0) return 0;
  const ms = at.getTime() - bounds.start.getTime();
  return Math.min(100, Math.max(0, (ms / bounds.totalMs) * 100));
}

export function percentWidth(bounds: DayBounds, start: Date, end: Date): number {
  const startPct = percentPosition(bounds, start);
  const endPct = percentPosition(bounds, end);
  return Math.max(0.15, endPct - startPct);
}

export const CATEGORY_COLOR: Record<Category, string> = {
  productive: "bg-success-500",
  neutral: "bg-brand-400",
  distraction: "bg-error-500",
  uncategorised: "bg-gray-300 dark:bg-gray-600",
};

export const CATEGORY_LABEL: Record<Category, string> = {
  productive: "Productive",
  neutral: "Neutral",
  distraction: "Distraction",
  uncategorised: "Uncategorised",
};

export function formatDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) return "0m";
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function formatClock(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}
