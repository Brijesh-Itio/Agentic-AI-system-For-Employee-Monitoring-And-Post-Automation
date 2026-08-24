import { AlertTriangle, Loader2, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import TeamComparisonChart from "./TeamComparisonChart";
import { getTeamAnalysis } from "@/api";

const RISK_VARIANT: Record<string, "destructive" | "warning" | "success"> = {
  high: "destructive",
  medium: "warning",
  low: "success",
};

interface TeamAnalysisPanelProps {
  anonymised: boolean;
}

export default function TeamAnalysisPanel({ anonymised }: TeamAnalysisPanelProps) {
  const query = useQuery({
    queryKey: ["team", "analysis"],
    queryFn: () => getTeamAnalysis(7),
    enabled: false,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">AI Team Analysis</h3>
          <p className="text-theme-xs text-gray-400">
            Weekly Ollama-powered read of every member's tracked data — module 21.4.
          </p>
        </div>
        <Button onClick={() => query.refetch()} disabled={query.isFetching}>
          {query.isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Run Analysis
        </Button>
      </div>

      {query.isError && (
        <p className="text-theme-sm text-error-600 dark:text-error-400">
          Analysis failed — check the backend and Ollama are reachable.
        </p>
      )}

      {!query.data && !query.isFetching && (
        <p className="py-6 text-center text-theme-sm text-gray-400">
          Run the analysis to see comparison charts and AI-generated team insights.
        </p>
      )}

      {query.data && (
        <div className="space-y-5">
          <TeamComparisonChart members={query.data.members} anonymised={anonymised} />

          {query.data.raw_summary ? (
            <div className="rounded-lg border border-gray-100 p-4 text-theme-sm text-gray-600 dark:border-gray-800 dark:text-gray-300">
              {query.data.raw_summary}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                <p className="mb-2 flex items-center gap-1.5 font-medium text-success-600 dark:text-success-400">
                  <TrendingUp className="h-4 w-4" /> High Performers
                </p>
                {query.data.high_performers.length === 0 ? (
                  <p className="text-theme-xs text-gray-400">None identified</p>
                ) : (
                  <ul className="space-y-1 text-theme-sm text-gray-600 dark:text-gray-300">
                    {query.data.high_performers.map((name) => (
                      <li key={name}>{anonymised ? "Member" : name}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                <p className="mb-2 flex items-center gap-1.5 font-medium text-warning-600 dark:text-warning-400">
                  <TrendingDown className="h-4 w-4" /> Struggling Members
                </p>
                {query.data.struggling_members.length === 0 ? (
                  <p className="text-theme-xs text-gray-400">None identified</p>
                ) : (
                  <ul className="space-y-1 text-theme-sm text-gray-600 dark:text-gray-300">
                    {query.data.struggling_members.map((name) => (
                      <li key={name}>{anonymised ? "Member" : name}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                <p className="mb-1 font-medium text-gray-900 dark:text-white">Workload Imbalance</p>
                <p className="text-theme-sm text-gray-600 dark:text-gray-300">
                  {query.data.workload_imbalance || "No signal yet"}
                </p>
              </div>

              <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                <p className="mb-1 font-medium text-gray-900 dark:text-white">Bottlenecks</p>
                <p className="text-theme-sm text-gray-600 dark:text-gray-300">{query.data.bottlenecks || "None identified"}</p>
              </div>

              <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800 md:col-span-2">
                <p className="mb-2 font-medium text-gray-900 dark:text-white">Rebalancing Suggestions</p>
                {query.data.rebalancing_suggestions.length === 0 ? (
                  <p className="text-theme-xs text-gray-400">No suggestions yet</p>
                ) : (
                  <ul className="list-disc space-y-1 pl-4 text-theme-sm text-gray-600 dark:text-gray-300">
                    {query.data.rebalancing_suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-lg border border-gray-100 p-4 dark:border-gray-800 md:col-span-2">
                <p className="mb-2 flex items-center gap-1.5 font-medium text-gray-900 dark:text-white">
                  <AlertTriangle className="h-4 w-4" /> Burnout Risk
                </p>
                {query.data.burnout_risk.length === 0 ? (
                  <p className="text-theme-xs text-gray-400">No risk data yet</p>
                ) : (
                  <div className="space-y-2">
                    {query.data.burnout_risk.map((b, i) => (
                      <div key={i} className="flex items-center justify-between gap-2 text-theme-sm">
                        <span className="text-gray-600 dark:text-gray-300">
                          {anonymised ? "Member" : b.name} — {b.reason}
                        </span>
                        <Badge variant={RISK_VARIANT[b.risk] ?? "outline"}>{b.risk}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
