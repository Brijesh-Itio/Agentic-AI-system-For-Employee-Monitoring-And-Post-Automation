import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import DateSelector from "@/components/Timeline/DateSelector";
import PeriodToggle from "@/components/Analytics/PeriodToggle";
import PeriodSummaryStats from "@/components/Analytics/PeriodSummaryStats";
import TopAppsBarChart from "@/components/Analytics/TopAppsBarChart";
import CategoryPieChart from "@/components/Analytics/CategoryPieChart";
import ScoreGauge from "@/components/Analytics/ScoreGauge";
import WeeklyTrendChart from "@/components/Analytics/WeeklyTrendChart";
import FocusSessionsSummary from "@/components/Analytics/FocusSessionsSummary";
import PeakHoursHeatmap from "@/components/Analytics/PeakHoursHeatmap";
import ContextSwitchingChart from "@/components/Analytics/ContextSwitchingChart";
import {
  getAppsSummaryByDate,
  getScoreByDate,
  getDailyScores,
  getFocusSessionsToday,
  getPeakHoursHeatmap,
  getPeriodSummary,
  getContextSwitchingByDate,
} from "@/api";

const todayStr = () => new Date().toISOString().slice(0, 10);
const shiftDate = (date: string, days: number) => {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

/** "Today" / "Yesterday" for the two nearby days, otherwise a short date
 * ("Aug 25") — keeps card titles and the score comparison label readable
 * however far back the user has picked. */
function dateLabel(date: string): string {
  if (date === todayStr()) return "Today";
  if (date === shiftDate(todayStr(), -1)) return "Yesterday";
  return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function AnalyticsPage() {
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [periodDays, setPeriodDays] = useState(7);
  const previousDate = useMemo(() => shiftDate(selectedDate, -1), [selectedDate]);
  const isToday = selectedDate === todayStr();

  const appsQuery = useQuery({
    queryKey: ["activity", "apps", "summary", selectedDate],
    queryFn: () => getAppsSummaryByDate(selectedDate),
  });
  const scoreQuery = useQuery({
    queryKey: ["productivity", "score", selectedDate],
    queryFn: () => getScoreByDate(selectedDate),
  });
  const previousScoreQuery = useQuery({
    queryKey: ["productivity", "score", previousDate],
    queryFn: () => getScoreByDate(previousDate),
  });
  const dailyScoresQuery = useQuery({
    queryKey: ["productivity", "daily-scores", periodDays],
    queryFn: () => getDailyScores(periodDays),
  });
  const periodSummaryQuery = useQuery({
    queryKey: ["productivity", "summary", periodDays],
    queryFn: () => getPeriodSummary(periodDays),
  });
  const focusSessionsQuery = useQuery({ queryKey: ["productivity", "focus-sessions"], queryFn: getFocusSessionsToday });
  // PeakHoursHeatmap always renders a fixed 7-column grid internally, so it
  // isn't wired to periodDays — feeding it a longer window would just get
  // silently truncated to 7 days while the title claimed otherwise.
  const heatmapQuery = useQuery({ queryKey: ["productivity", "heatmap"], queryFn: () => getPeakHoursHeatmap(7) });
  const switchingQuery = useQuery({
    queryKey: ["context-switching", selectedDate],
    queryFn: () => getContextSwitchingByDate(selectedDate),
  });

  return (
    <>
      <PageMeta title="Analytics | WorkPulse AI" description="App usage, focus trends, and productivity charts." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Analytics</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              App usage breakdown, focus score trends, and peak performance windows.
            </p>
          </div>
          <DateSelector date={selectedDate} onChange={setSelectedDate} />
        </div>

        <FocusSessionsSummary summary={focusSessionsQuery.data} loading={focusSessionsQuery.isLoading} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Top Apps — {dateLabel(selectedDate)}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <TopAppsBarChart apps={appsQuery.data ?? []} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Focus Score — {dateLabel(selectedDate)}</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-center pt-0">
              <ScoreGauge
                score={scoreQuery.data?.focus_score ?? null}
                yesterdayScore={previousScoreQuery.data?.focus_score ?? null}
                compareLabel={isToday ? "yesterday" : dateLabel(previousDate).toLowerCase()}
              />
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Category Split — {dateLabel(selectedDate)}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <CategoryPieChart apps={appsQuery.data ?? []} />
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle>{periodDays}-Day Focus Trend</CardTitle>
              <PeriodToggle value={periodDays} onChange={setPeriodDays} />
            </CardHeader>
            <CardContent className="pt-0">
              <WeeklyTrendChart scores={dailyScoresQuery.data ?? []} />
            </CardContent>
          </Card>
        </div>

        <div>
          <h2 className="mb-3 text-theme-sm font-semibold text-gray-700 dark:text-gray-300">
            Last {periodDays} Days Average
          </h2>
          <PeriodSummaryStats summary={periodSummaryQuery.data} loading={periodSummaryQuery.isLoading} />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Peak Hours Heatmap — Last 7 Days</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <PeakHoursHeatmap cells={heatmapQuery.data ?? []} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Context Switching — {dateLabel(selectedDate)}</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ContextSwitchingChart hours={switchingQuery.data ?? []} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
