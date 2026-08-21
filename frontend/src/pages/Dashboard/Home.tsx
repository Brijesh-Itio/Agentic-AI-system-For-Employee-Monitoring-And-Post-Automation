import { useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Brain,
  Cpu,
  Mail,
  Gauge,
  Timer,
  LayoutGrid,
  FileText,
  Briefcase,
  Send,
  Clock,
  Loader2,
} from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import StatCard from "@/components/dashboard/StatCard";
import { getStatus, getTodayScore, getTodayAppsSummary, generateDarNow } from "@/api";

const REFRESH_INTERVAL_MS = 30_000;

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function DashboardHome() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [darMessage, setDarMessage] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: ["status"],
    queryFn: getStatus,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const scoreQuery = useQuery({
    queryKey: ["productivity", "today"],
    queryFn: getTodayScore,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const appsQuery = useQuery({
    queryKey: ["activity", "apps", "summary"],
    queryFn: getTodayAppsSummary,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const darMutation = useMutation({
    mutationFn: generateDarNow,
    onMutate: () => setDarMessage("Generating your report locally with Ollama — this can take a couple of minutes."),
    onSuccess: () => {
      setDarMessage("DAR generated successfully.");
      queryClient.invalidateQueries({ queryKey: ["dar"] });
    },
    onError: () =>
      setDarMessage("DAR generation failed — Ollama may be unreachable or timed out. Check that it's running."),
  });

  const focusScore = scoreQuery.data?.focus_score;
  const activeHours = scoreQuery.data?.productive_hours_formatted ?? "0h 0m";
  const appsTracked = appsQuery.data?.length ?? 0;

  return (
    <>
      <PageMeta
        title="Dashboard | WorkPulse AI"
        description="Your agentic AI work intelligence and automation command centre."
      />

      <div className="space-y-6">
        {/* Hero */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 via-brand-500 to-indigo-600 p-6 text-white shadow-lg shadow-brand-500/20 sm:p-8">
          <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
          <div className="relative">
            <p className="text-sm font-medium text-white/80">{greeting()}</p>
            <h1 className="mt-1 text-2xl font-bold sm:text-3xl">Your day at a glance</h1>
            <p className="mt-2 max-w-xl text-sm text-white/80">
              WorkPulse AI is watching, thinking, and acting — tracking your work, scoring your
              focus, and preparing tonight's report, all running locally.
            </p>
          </div>
        </div>

        {/* Status cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label="Ollama AI"
            value={statusQuery.data ? (statusQuery.data.ollama.connected ? "Running" : "Offline") : "—"}
            icon={Brain}
            tone={statusQuery.data?.ollama.connected ? "success" : "error"}
            hint={statusQuery.data?.ollama.detail}
            loading={statusQuery.isLoading}
          />
          <StatCard
            label="Desktop Agent"
            value={statusQuery.data ? (statusQuery.data.agent.connected ? "Running" : "Offline") : "—"}
            icon={Cpu}
            tone={statusQuery.data?.agent.connected ? "success" : "error"}
            hint={statusQuery.data?.agent.detail}
            loading={statusQuery.isLoading}
          />
          <StatCard
            label="Gmail"
            value={statusQuery.data ? (statusQuery.data.gmail.connected ? "Connected" : "Offline") : "—"}
            icon={Mail}
            tone={statusQuery.data?.gmail.connected ? "success" : "warning"}
            hint={statusQuery.data?.gmail.detail}
            loading={statusQuery.isLoading}
          />
          <StatCard
            label="Today's Focus Score"
            value={focusScore != null ? `${Math.round(focusScore)}%` : "No data yet"}
            icon={Gauge}
            tone={focusScore != null && focusScore >= 60 ? "success" : "neutral"}
            loading={scoreQuery.isLoading}
          />
          <StatCard
            label="Active Hours Today"
            value={activeHours}
            icon={Timer}
            loading={scoreQuery.isLoading}
          />
          <StatCard
            label="Total Apps Tracked"
            value={String(appsTracked)}
            icon={LayoutGrid}
            loading={appsQuery.isLoading}
          />
        </div>

        {/* Quick actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3 pt-0">
            <Button onClick={() => darMutation.mutate()} disabled={darMutation.isPending}>
              {darMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              Generate DAR Now
            </Button>
            <Button variant="outline" onClick={() => navigate("/timeline")}>
              <Clock className="h-4 w-4" />
              View Today's Timeline
            </Button>
            <Button variant="secondary" disabled title="Coming in Module 18 — LinkedIn Automation">
              <Briefcase className="h-4 w-4" />
              Post to LinkedIn
            </Button>
            <Button variant="secondary" disabled title="Coming in Module 19 — Email Campaign Automation">
              <Send className="h-4 w-4" />
              Run Email Campaign
            </Button>
          </CardContent>
          {darMessage && (
            <div className="px-6 pb-6">
              <p className="text-theme-sm text-gray-500 dark:text-gray-400">{darMessage}</p>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
