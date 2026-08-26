import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import type { DailyScore } from "@/api";

interface WeeklyTrendSparklineProps {
  scores: DailyScore[];
}

/** Compact axis-less trend glyph for the hero — not a full chart, a single
 * headline metric's supporting context (7-day shape), so it skips axes,
 * legend and gridlines entirely. Single series only, so identity is never
 * in question and no legend is needed. */
export default function WeeklyTrendSparkline({ scores }: WeeklyTrendSparklineProps) {
  const data = scores.map((s) => ({
    day: new Date(`${s.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short" }),
    score: s.focus_score,
  }));

  const hasAnyData = data.some((d) => d.score != null);
  if (!hasAnyData) {
    return <div className="flex h-14 items-center text-theme-xs text-white/60">No trend data yet</div>;
  }

  return (
    <div className="h-14 w-full sm:w-40">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
          <defs>
            <linearGradient id="heroSparklineFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffffff" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#ffffff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Tooltip
            cursor={false}
            contentStyle={{ borderRadius: 8, fontSize: 11, padding: "4px 8px" }}
            formatter={(value: unknown) => [typeof value === "number" ? `${Math.round(value)}%` : "No data", "Focus"]}
            labelFormatter={(label) => label}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="#ffffff"
            strokeWidth={2}
            fill="url(#heroSparklineFill)"
            connectNulls
            dot={false}
            activeDot={{ r: 3, fill: "#ffffff", stroke: "none" }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
      <p className="mt-0.5 text-center text-[10px] font-medium uppercase tracking-wide text-white/60">
        Last 7 days
      </p>
    </div>
  );
}
