import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/shadcn/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  tone?: "neutral" | "success" | "warning" | "error";
  hint?: string;
  loading?: boolean;
}

const toneClasses: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400",
  success: "bg-success-50 text-success-600 dark:bg-success-500/10 dark:text-success-400",
  warning: "bg-warning-50 text-warning-600 dark:bg-warning-500/10 dark:text-warning-400",
  error: "bg-error-50 text-error-600 dark:bg-error-500/10 dark:text-error-400",
};

export default function StatCard({ label, value, icon: Icon, tone = "neutral", hint, loading }: StatCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div className="min-w-0">
          <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">{label}</p>
          {loading ? (
            <div className="mt-2 h-6 w-20 animate-pulse rounded bg-gray-100 dark:bg-white/5" />
          ) : (
            <p className="mt-1 truncate text-title-sm font-semibold text-gray-900 dark:text-white">
              {value}
            </p>
          )}
          {hint && !loading && (
            <p className="mt-1 text-theme-xs text-gray-400 dark:text-gray-500">{hint}</p>
          )}
        </div>
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl", toneClasses[tone])}>
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}
