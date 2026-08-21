import { RadialBar, RadialBarChart, PolarAngleAxis } from "recharts";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { COLORS } from "./chartColors";

interface ScoreGaugeProps {
  score: number | null;
  yesterdayScore: number | null;
}

function colorFor(score: number): string {
  if (score >= 70) return COLORS.success;
  if (score >= 40) return COLORS.warning;
  return COLORS.error;
}

export default function ScoreGauge({ score, yesterdayScore }: ScoreGaugeProps) {
  const value = score ?? 0;
  const data = [{ value, fill: colorFor(value) }];

  const delta = score != null && yesterdayScore != null ? score - yesterdayScore : null;

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <RadialBarChart
          width={180}
          height={180}
          cx="50%"
          cy="50%"
          innerRadius="75%"
          outerRadius="100%"
          barSize={14}
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar dataKey="value" cornerRadius={8} background={{ fill: "#f2f4f7" }} />
        </RadialBarChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-gray-900 dark:text-white">
            {score != null ? Math.round(score) : "—"}
          </span>
          {score != null && <span className="text-theme-xs text-gray-400">/ 100</span>}
        </div>
      </div>

      {delta != null ? (
        <div
          className={`mt-2 flex items-center gap-1 text-theme-xs font-medium ${
            delta > 0 ? "text-success-600" : delta < 0 ? "text-error-600" : "text-gray-400"
          }`}
        >
          {delta > 0 ? <TrendingUp className="h-3.5 w-3.5" /> : delta < 0 ? <TrendingDown className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
          {delta === 0 ? "Same as yesterday" : `${Math.abs(Math.round(delta))} pts vs yesterday`}
        </div>
      ) : (
        <p className="mt-2 text-theme-xs text-gray-400">No comparison data yet</p>
      )}
    </div>
  );
}
