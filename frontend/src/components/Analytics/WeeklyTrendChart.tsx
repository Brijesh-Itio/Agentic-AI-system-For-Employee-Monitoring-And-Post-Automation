import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DailyScore } from "@/api";
import { COLORS } from "./chartColors";

interface WeeklyTrendChartProps {
  scores: DailyScore[];
}

export default function WeeklyTrendChart({ scores }: WeeklyTrendChartProps) {
  // A short weekday name ("Mon") only stays unambiguous across a single
  // week — once the caller feeds a longer window (14d/30d), the same label
  // would repeat several times, so fall back to a dated label instead.
  const dateFormat: Intl.DateTimeFormatOptions =
    scores.length > 7 ? { month: "short", day: "numeric" } : { weekday: "short" };
  const data = scores.map((s) => ({
    day: new Date(`${s.date}T00:00:00`).toLocaleDateString(undefined, dateFormat),
    score: s.focus_score,
  }));

  const scored = data.filter((d) => d.score != null) as { day: string; score: number }[];
  const average = scored.length ? scored.reduce((sum, d) => sum + d.score, 0) / scored.length : null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ left: -20, right: 12, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-gray-100 dark:stroke-white/5" />
        <XAxis dataKey="day" tick={{ fontSize: 12 }} className="fill-gray-500 dark:fill-gray-400" />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} className="fill-gray-500 dark:fill-gray-400" />
        <Tooltip
          formatter={(value: unknown) =>
            typeof value === "number" ? [`${Math.round(value)}%`, "Score"] : ["No data", "Score"]
          }
          contentStyle={{ borderRadius: 8, fontSize: 12 }}
        />
        {average != null && (
          <ReferenceLine
            y={average}
            stroke={COLORS.gray}
            strokeDasharray="4 4"
            label={{ value: `Avg ${Math.round(average)}%`, fontSize: 11, fill: "#98a2b3", position: "insideTopLeft" }}
          />
        )}
        <Line
          type="monotone"
          dataKey="score"
          stroke={COLORS.brand}
          strokeWidth={2.5}
          dot={{ r: 4, fill: COLORS.brand }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
