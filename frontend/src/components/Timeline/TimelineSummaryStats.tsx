import { Clock, CheckCircle2, AlertTriangle, Repeat2 } from "lucide-react";
import StatCard from "@/components/dashboard/StatCard";
import type { ActivityLogEntry, ContextSwitchingHour } from "@/api";
import { formatDuration } from "./timeScale";

interface TimelineSummaryStatsProps {
  sessions: ActivityLogEntry[];
  switching: ContextSwitchingHour[];
  loading: boolean;
}

export default function TimelineSummaryStats({ sessions, switching, loading }: TimelineSummaryStatsProps) {
  const totalSeconds = sessions.reduce((sum, s) => sum + (s.duration_seconds ?? 0), 0);
  const productiveSeconds = sessions
    .filter((s) => s.category === "productive")
    .reduce((sum, s) => sum + (s.duration_seconds ?? 0), 0);
  const distractionSeconds = sessions
    .filter((s) => s.category === "distraction")
    .reduce((sum, s) => sum + (s.duration_seconds ?? 0), 0);
  const totalSwitches = switching.reduce((sum, h) => sum + h.switch_count, 0);

  const pct = (seconds: number) => (totalSeconds > 0 ? Math.round((seconds / totalSeconds) * 100) : 0);

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard label="Total Tracked" value={formatDuration(totalSeconds)} icon={Clock} loading={loading} />
      <StatCard
        label="Productive"
        value={formatDuration(productiveSeconds)}
        hint={totalSeconds > 0 ? `${pct(productiveSeconds)}% of tracked time` : undefined}
        icon={CheckCircle2}
        tone="success"
        loading={loading}
      />
      <StatCard
        label="Distraction"
        value={formatDuration(distractionSeconds)}
        hint={totalSeconds > 0 ? `${pct(distractionSeconds)}% of tracked time` : undefined}
        icon={AlertTriangle}
        tone={distractionSeconds > 0 ? "warning" : "neutral"}
        loading={loading}
      />
      <StatCard
        label="Context Switches"
        value={String(totalSwitches)}
        icon={Repeat2}
        tone={totalSwitches > 30 ? "warning" : "neutral"}
        loading={loading}
      />
    </div>
  );
}
