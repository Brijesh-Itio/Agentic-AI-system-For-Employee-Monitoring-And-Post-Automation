import { Flame, Timer, Trophy, AlertTriangle } from "lucide-react";
import StatCard from "@/components/dashboard/StatCard";
import type { FocusSessionsSummary as FocusSessionsSummaryType } from "@/api";
import { formatDuration } from "@/components/Timeline/timeScale";

interface FocusSessionsSummaryProps {
  summary: FocusSessionsSummaryType | undefined;
  loading: boolean;
}

export default function FocusSessionsSummary({ summary, loading }: FocusSessionsSummaryProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard label="Focus Sessions Today" value={String(summary?.session_count ?? 0)} icon={Flame} loading={loading} />
      <StatCard
        label="Average Session"
        value={formatDuration(summary?.average_session_seconds ?? 0)}
        icon={Timer}
        loading={loading}
      />
      <StatCard
        label="Longest Session"
        value={formatDuration(summary?.longest_session_seconds ?? 0)}
        icon={Trophy}
        tone="success"
        loading={loading}
      />
      <StatCard
        label="Interrupted by Distraction"
        value={String(summary?.interrupted_count ?? 0)}
        icon={AlertTriangle}
        tone={summary && summary.interrupted_count > 0 ? "warning" : "neutral"}
        loading={loading}
      />
    </div>
  );
}
