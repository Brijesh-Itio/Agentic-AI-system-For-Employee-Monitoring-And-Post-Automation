import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MemberWeeklyStats } from "@/api";
import { COLORS } from "@/components/Analytics/chartColors";

interface TeamComparisonChartProps {
  members: MemberWeeklyStats[];
  anonymised: boolean;
}

export default function TeamComparisonChart({ members, anonymised }: TeamComparisonChartProps) {
  const data = members.map((m, i) => ({
    name: anonymised ? `Member ${i + 1}` : m.name,
    "Focus Score": m.avg_focus_score ?? 0,
    "Productive Hours": m.productive_hours,
    "Avg Switches/Day": m.avg_switch_count,
  }));

  if (data.length === 0) {
    return <div className="flex h-64 items-center justify-center text-theme-sm text-gray-400">No team members registered yet</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ left: -20, right: 12, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-gray-100 dark:stroke-white/5" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} className="fill-gray-500 dark:fill-gray-400" />
        <YAxis tick={{ fontSize: 12 }} className="fill-gray-500 dark:fill-gray-400" />
        <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Focus Score" fill={COLORS.brand} radius={[4, 4, 0, 0]} />
        <Bar dataKey="Productive Hours" fill={COLORS.success} radius={[4, 4, 0, 0]} />
        <Bar dataKey="Avg Switches/Day" fill={COLORS.warning} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
