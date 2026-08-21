import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ContextSwitchingHour } from "@/api";
import { COLORS } from "./chartColors";
import { CONTEXT_SWITCH_HIGH_THRESHOLD } from "@/components/Timeline/thresholds";

interface ContextSwitchingChartProps {
  hours: ContextSwitchingHour[];
}

export default function ContextSwitchingChart({ hours }: ContextSwitchingChartProps) {
  const byHour = new Map(hours.map((h) => [h.hour, h.switch_count]));
  const data = Array.from({ length: 24 }, (_, hour) => ({
    hour: `${hour}:00`,
    switches: byHour.get(hour) ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ left: -20, right: 12, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-gray-100 dark:stroke-white/5" />
        <XAxis dataKey="hour" interval={2} tick={{ fontSize: 11 }} className="fill-gray-500 dark:fill-gray-400" />
        <YAxis tick={{ fontSize: 12 }} className="fill-gray-500 dark:fill-gray-400" />
        <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
        <ReferenceLine
          y={CONTEXT_SWITCH_HIGH_THRESHOLD}
          stroke={COLORS.error}
          strokeDasharray="4 4"
          label={{ value: "Alert threshold", fontSize: 11, fill: COLORS.error, position: "insideTopRight" }}
        />
        <Bar dataKey="switches" fill={COLORS.brandLight} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
