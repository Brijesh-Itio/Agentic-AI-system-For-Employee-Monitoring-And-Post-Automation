import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { AppSummary } from "@/api";
import { CATEGORY_HEX } from "./chartColors";
import { formatDuration } from "@/components/Timeline/timeScale";

interface CategoryPieChartProps {
  apps: AppSummary[];
}

const LABELS: Record<string, string> = {
  productive: "Productive",
  neutral: "Neutral",
  distraction: "Distraction",
};

export default function CategoryPieChart({ apps }: CategoryPieChartProps) {
  const totals: Record<string, number> = { productive: 0, neutral: 0, distraction: 0 };
  for (const app of apps) {
    if (app.category in totals) totals[app.category] += app.total_seconds;
  }
  const grandTotal = totals.productive + totals.neutral + totals.distraction;
  const data = Object.entries(totals)
    .filter(([, seconds]) => seconds > 0)
    .map(([category, seconds]) => ({ category, seconds, pct: grandTotal ? (seconds / grandTotal) * 100 : 0 }));

  if (data.length === 0) {
    return <div className="flex h-56 items-center justify-center text-theme-sm text-gray-400">No categorised time yet</div>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={data} dataKey="seconds" nameKey="category" innerRadius={55} outerRadius={85} paddingAngle={2}>
            {data.map((entry) => (
              <Cell key={entry.category} fill={CATEGORY_HEX[entry.category]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(_v, _n, item) => [formatDuration(item.payload.seconds), LABELS[item.payload.category]]}
            contentStyle={{ borderRadius: 8, fontSize: 12 }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap justify-center gap-4">
        {data.map((entry) => (
          <div key={entry.category} className="flex items-center gap-1.5 text-theme-xs">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: CATEGORY_HEX[entry.category] }} />
            <span className="text-gray-600 dark:text-gray-300">{LABELS[entry.category]}</span>
            <span className="text-gray-400">
              {entry.pct.toFixed(0)}% · {formatDuration(entry.seconds)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
