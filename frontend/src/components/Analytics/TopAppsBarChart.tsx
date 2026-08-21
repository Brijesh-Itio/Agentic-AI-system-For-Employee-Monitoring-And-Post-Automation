import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AppSummary } from "@/api";
import { CATEGORY_HEX } from "./chartColors";
import { formatDuration } from "@/components/Timeline/timeScale";

interface TopAppsBarChartProps {
  apps: AppSummary[];
}

export default function TopAppsBarChart({ apps }: TopAppsBarChartProps) {
  const data = [...apps]
    .sort((a, b) => b.total_seconds - a.total_seconds)
    .slice(0, 10)
    .map((a) => ({ ...a, hours: a.total_seconds / 3600 }));

  if (data.length === 0) {
    return <div className="flex h-64 items-center justify-center text-theme-sm text-gray-400">No app data yet</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(240, data.length * 36)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="app_name"
          width={110}
          tick={{ fontSize: 12, fill: "currentColor" }}
          className="text-gray-500 dark:text-gray-400"
        />
        <Tooltip
          formatter={(_value, _name, item) => [formatDuration(item.payload.total_seconds), "Time"]}
          contentStyle={{ borderRadius: 8, fontSize: 12 }}
        />
        <Bar dataKey="hours" radius={[0, 4, 4, 0]} barSize={18}>
          {data.map((entry) => (
            <Cell key={entry.app_name} fill={CATEGORY_HEX[entry.category] ?? CATEGORY_HEX.uncategorised} />
          ))}
          <LabelList
            dataKey="total_seconds"
            position="right"
            formatter={(v: unknown) => (typeof v === "number" ? formatDuration(v) : "")}
            style={{ fontSize: 11, fill: "currentColor" }}
            className="fill-gray-500 dark:fill-gray-400"
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
