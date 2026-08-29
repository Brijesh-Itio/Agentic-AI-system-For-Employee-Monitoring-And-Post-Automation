import type { LucideIcon } from "lucide-react";

export interface StatStripItem {
  label: string;
  value: string;
  icon: LucideIcon;
  valueClassName?: string;
  hint?: string;
  loading?: boolean;
}

/** One bordered strip with internal dividers reads as a single dashboard
 * metric row — several separately-shadowed cards for numbers this related
 * just repeats the same card chrome over and over and reads as clutter.
 * `auto-fit` sizes the column count to whatever fits rather than needing a
 * breakpoint prop tuned per caller. */
export default function StatStrip({ stats, minColumnWidth = 150 }: { stats: StatStripItem[]; minColumnWidth?: number }) {
  return (
    <div
      className="grid overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]"
      style={{ gridTemplateColumns: `repeat(auto-fit, minmax(${minColumnWidth}px, 1fr))` }}
    >
      {stats.map((s) => (
        <div
          key={s.label}
          className="flex flex-col gap-1.5 border-b border-r border-gray-100 px-4 py-3.5 last:border-r-0 dark:border-gray-800"
        >
          <div className="flex items-center gap-1.5 text-gray-400 dark:text-gray-500">
            <s.icon className="h-3.5 w-3.5" />
            <span className="text-theme-xs font-medium">{s.label}</span>
          </div>
          {s.loading ? (
            <div className="h-6 w-10 animate-pulse rounded bg-gray-100 dark:bg-white/5" />
          ) : (
            <span className={`text-lg font-semibold text-gray-900 dark:text-white ${s.valueClassName ?? ""}`}>
              {s.value}
            </span>
          )}
          {s.hint && !s.loading && <span className="text-[10px] text-gray-400 dark:text-gray-500">{s.hint}</span>}
        </div>
      ))}
    </div>
  );
}
