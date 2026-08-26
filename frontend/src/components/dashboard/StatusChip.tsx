import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusChipProps {
  label: string;
  value: string;
  icon: LucideIcon;
  tone?: "neutral" | "success" | "warning" | "error";
  hint?: string;
  loading?: boolean;
}

const dotClasses: Record<NonNullable<StatusChipProps["tone"]>, string> = {
  neutral: "bg-gray-300 dark:bg-gray-600",
  success: "bg-success-500",
  warning: "bg-warning-500",
  error: "bg-error-500",
};

/** A binary/state indicator (is a service up?) is a different job from a KPI
 * (StatCard) — status colors here are reserved for state, never reused as a
 * generic categorical accent, and shown with an icon + label, never a bare
 * dot. Compact by design: system status is supporting context, not the
 * dashboard's headline content. */
export default function StatusChip({ label, value, icon: Icon, tone = "neutral", hint, loading }: StatusChipProps) {
  return (
    <div
      title={hint}
      className="flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-white/[0.02]"
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="truncate text-theme-xs text-gray-400">{label}</p>
        {loading ? (
          <div className="mt-1 h-3.5 w-16 animate-pulse rounded bg-gray-100 dark:bg-white/5" />
        ) : (
          <div className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", dotClasses[tone])} />
            <span className="truncate text-theme-sm font-medium text-gray-800 dark:text-gray-200">{value}</span>
          </div>
        )}
      </div>
    </div>
  );
}
