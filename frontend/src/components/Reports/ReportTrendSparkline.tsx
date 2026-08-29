import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";
import type { DarReport } from "@/api";
import { COLORS } from "@/components/Analytics/chartColors";

/** A quiet at-a-glance trend above the report list — no axes/gridlines by
 * design, it's a glance-level signal, not a chart meant to be read exactly. */
export default function ReportTrendSparkline({ reports }: { reports: DarReport[] }) {
  const data = [...reports]
    .filter((r) => r.productivity_score != null)
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((r) => ({ date: r.date, score: r.productivity_score as number }));

  if (data.length < 2) return null;

  return (
    <div className="h-10 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <YAxis domain={[0, 100]} hide />
          <defs>
            <linearGradient id="reportSparkFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS.brand} stopOpacity={0.25} />
              <stop offset="100%" stopColor={COLORS.brand} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="score" stroke={COLORS.brand} strokeWidth={1.75} fill="url(#reportSparkFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
