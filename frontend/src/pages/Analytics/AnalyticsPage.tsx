import { useQuery } from "@tanstack/react-query";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import TopAppsBarChart from "@/components/Analytics/TopAppsBarChart";
import CategoryPieChart from "@/components/Analytics/CategoryPieChart";
import ScoreGauge from "@/components/Analytics/ScoreGauge";
import WeeklyTrendChart from "@/components/Analytics/WeeklyTrendChart";
import FocusSessionsSummary from "@/components/Analytics/FocusSessionsSummary";
import PeakHoursHeatmap from "@/components/Analytics/PeakHoursHeatmap";
import ContextSwitchingChart from "@/components/Analytics/ContextSwitchingChart";
import {
  getTodayAppsSummary,
  getTodayScore,
  getScoreByDate,
  getDailyScores,
  getFocusSessionsToday,
  getPeakHoursHeatmap,
  getContextSwitchingByDate,
} from "@/api";

const todayStr = () => new Date().toISOString().slice(0, 10);
const yesterdayStr = () => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
};

export default function AnalyticsPage() {
  const appsQuery = useQuery({ queryKey: ["activity", "apps", "summary"], queryFn: getTodayAppsSummary });
  const todayScoreQuery = useQuery({ queryKey: ["productivity", "today"], queryFn: getTodayScore });
  const yesterdayScoreQuery = useQuery({
    queryKey: ["productivity", "score", yesterdayStr()],
    queryFn: () => getScoreByDate(yesterdayStr()),
  });
  const dailyScoresQuery = useQuery({ queryKey: ["productivity", "daily-scores"], queryFn: () => getDailyScores(7) });
  const focusSessionsQuery = useQuery({ queryKey: ["productivity", "focus-sessions"], queryFn: getFocusSessionsToday });
  const heatmapQuery = useQuery({ queryKey: ["productivity", "heatmap"], queryFn: () => getPeakHoursHeatmap(7) });
  const switchingQuery = useQuery({
    queryKey: ["context-switching", todayStr()],
    queryFn: () => getContextSwitchingByDate(todayStr()),
  });

  return (
    <>
      <PageMeta title="Analytics | WorkPulse AI" description="App usage, focus trends, and productivity charts." />

      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Analytics</h1>
          <p className="text-theme-sm text-gray-500 dark:text-gray-400">
            App usage breakdown, focus score trends, and peak performance windows.
          </p>
        </div>

        <FocusSessionsSummary summary={focusSessionsQuery.data} loading={focusSessionsQuery.isLoading} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Top Apps Today</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <TopAppsBarChart apps={appsQuery.data ?? []} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Today's Focus Score</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-center pt-0">
              <ScoreGauge score={todayScoreQuery.data?.focus_score ?? null} yesterdayScore={yesterdayScoreQuery.data?.focus_score ?? null} />
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Category Split</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <CategoryPieChart apps={appsQuery.data ?? []} />
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>7-Day Focus Trend</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <WeeklyTrendChart scores={dailyScoresQuery.data ?? []} />
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Peak Hours Heatmap</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <PeakHoursHeatmap cells={heatmapQuery.data ?? []} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Context Switching Today</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ContextSwitchingChart hours={switchingQuery.data ?? []} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
