import type { ActivityLogEntry, Category, IdlePeriod, ScreenshotEntry } from "@/api";

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

export interface HourMark {
  position: number;
  hour: number;
  label: string;
}

/** One gridline per whole hour inside the visible window — the track has
 * no reference points otherwise, so reading off a time meant hovering
 * every single segment. */
export function hourMarks(bounds: DayBounds): HourMark[] {
  if (bounds.totalMs <= 0) return [];
  const marks: HourMark[] = [];
  const cursor = new Date(bounds.start);
  cursor.setMinutes(0, 0, 0);
  if (cursor < bounds.start) cursor.setHours(cursor.getHours() + 1);

  while (cursor <= bounds.end) {
    marks.push({
      position: percentPosition(bounds, cursor),
      hour: cursor.getHours(),
      label: cursor.toLocaleTimeString(undefined, { hour: "numeric" }),
    });
    cursor.setHours(cursor.getHours() + 1);
  }
  return marks;
}

export interface ScreenshotCluster {
  position: number;
  shots: ScreenshotEntry[];
}

/** Screenshots taken minutes apart render at nearly the same x position and
 * their circular markers overlap into an unreadable solid strip once a day
 * has more than a handful — group anything within `thresholdPercent` of the
 * previous marker into one cluster instead. */
export function clusterScreenshots(
  bounds: DayBounds,
  screenshots: ScreenshotEntry[],
  thresholdPercent = 1.4
): ScreenshotCluster[] {
  const sorted = [...screenshots].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const clusters: ScreenshotCluster[] = [];
  for (const shot of sorted) {
    const position = percentPosition(bounds, new Date(shot.timestamp));
    const current = clusters[clusters.length - 1];
    if (current && position - current.position <= thresholdPercent) {
      current.shots.push(shot);
    } else {
      clusters.push({ position, shots: [shot] });
    }
  }
  return clusters;
}
