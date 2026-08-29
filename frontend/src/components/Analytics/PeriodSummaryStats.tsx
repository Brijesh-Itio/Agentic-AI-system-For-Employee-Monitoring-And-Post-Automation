import { TrendingUp, Clock, CheckCircle2, CalendarDays } from "lucide-react";
import StatCard from "@/components/dashboard/StatCard";
import type { PeriodSummary } from "@/api";

interface PeriodSummaryStatsProps {
  summary: PeriodSummary | undefined;
  loading: boolean;
}

export default function PeriodSummaryStats({ summary, loading }: PeriodSummaryStatsProps) {
  const hasScore = summary?.avg_focus_score != null;

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard
        label="Avg Focus Score"
        value={hasScore ? `${Math.round(summary!.avg_focus_score!)}%` : "—"}
        icon={TrendingUp}
        tone="success"
        loading={loading}
      />
      <StatCard
        label="Avg Active Time"
        value={summary?.avg_active_hours_formatted ?? "0h 0m"}
        icon={Clock}
        loading={loading}
      />
      <StatCard
        label="Avg Productive Time"
        value={summary?.avg_productive_hours_formatted ?? "0h 0m"}
        icon={CheckCircle2}
        tone="success"
        loading={loading}
      />
      <StatCard
        label="Days Tracked"
        value={summary ? `${summary.days_tracked} / ${summary.days_requested}` : "—"}
        icon={CalendarDays}
        loading={loading}
      />
    </div>
  );
}
