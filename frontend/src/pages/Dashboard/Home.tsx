import { useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Brain,
  Cpu,
  Mail,
  Timer,
  LayoutGrid,
  FileText,
  Briefcase,
  Clock,
  Coffee,
  Loader2,
  LogIn,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Minus,
  Send,
} from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/shadcn/card";
import StatCard from "@/components/dashboard/StatCard";
import StatusChip from "@/components/dashboard/StatusChip";
import WeeklyTrendSparkline from "@/components/dashboard/WeeklyTrendSparkline";
import { getStatus, getTodayScore, getTodayAppsSummary, getDailyScores, generateDarNow } from "@/api";

const REFRESH_INTERVAL_MS = 30_000;

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

interface QuickAction {
  label: string;
  description: string;
  icon: typeof FileText;
  onClick: () => void;
  isPending?: boolean;
  isPrimary?: boolean;
}

function QuickActionTile({ label, description, icon: Icon, onClick, isPending, isPrimary }: QuickAction) {
  return (
    <button
      onClick={onClick}
      disabled={isPending}
      className={`group flex items-start gap-3.5 rounded-xl border p-4 text-left transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-70 ${
        isPrimary
          ? "border-brand-200 bg-brand-50/60 dark:border-brand-500/20 dark:bg-brand-500/[0.06]"
          : "border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.02]"
      }`}
    >
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
          isPrimary
            ? "bg-brand-500 text-white"
            : "bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400"
        }`}
      >
        {isPending ? <Loader2 className="h-4.5 w-4.5 animate-spin" /> : <Icon className="h-4.5 w-4.5" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-theme-sm font-semibold text-gray-800 dark:text-gray-200">{label}</p>
        <p className="mt-0.5 text-theme-xs text-gray-400">{description}</p>
      </div>
      <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-gray-300 transition-transform group-hover:translate-x-0.5 group-hover:text-gray-400 dark:text-gray-600" />
    </button>
  );
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

  const weeklyScoresQuery = useQuery({
    queryKey: ["productivity", "daily-scores", 7],
    queryFn: () => getDailyScores(7),
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
  const activeHours = scoreQuery.data?.active_hours_formatted ?? "0h 0m";
  const idleTime = scoreQuery.data?.idle_formatted ?? "0h 0m";
  const appsTracked = appsQuery.data?.length ?? 0;

  const scores = weeklyScoresQuery.data ?? [];
  const scoredDays = scores.filter((s) => s.focus_score != null);
  const yesterdayScore = scoredDays.length >= 2 ? scoredDays[scoredDays.length - 2].focus_score : null;
  const scoreDelta = focusScore != null && yesterdayScore != null ? focusScore - yesterdayScore : null;

  // work_start/work_end aren't a manual clock-in — they're set automatically
  // from the first and last tracked activity of the day. work_end used to
  // only update when a break >=15min ended (stamped at the break's start),
  // so it froze there until the next such break — a lunch break made this
  // read as "checked out" for the rest of the afternoon. TimeIntelligenceEngine
  // now advances work_end continuously while active (every ~30s), so it
  // resumes climbing the moment work picks back up after a break.
  const formatTime = (iso: string | null) =>
    iso ? new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true }) : null;
  const workStart = formatTime(scoreQuery.data?.work_start ?? null);
  const workEnd = formatTime(scoreQuery.data?.work_end ?? null);
  const workHoursValue = workStart ? `${workStart} – ${workEnd ?? "now"}` : "Not started yet";

  const quickActions: QuickAction[] = [
    {
      label: "Generate DAR Now",
      description: "AI-written daily report via Ollama",
      icon: FileText,
      onClick: () => darMutation.mutate(),
      isPending: darMutation.isPending,
      isPrimary: true,
    },
    {
      label: "View Today's Timeline",
      description: "Minute-by-minute activity breakdown",
      icon: Clock,
      onClick: () => navigate("/timeline"),
    },
    {
      label: "Post to LinkedIn",
      description: "AI-drafted post, ready to publish",
      icon: Briefcase,
      onClick: () => navigate("/linkedin"),
    },
    {
      label: "Run Email Campaign",
      description: "Personalised outreach via RAG",
      icon: Send,
      onClick: () => navigate("/email"),
    },
  ];

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
          <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-white/80">{greeting()}</p>
              <h1 className="mt-1 text-2xl font-bold sm:text-3xl">Your day at a glance</h1>
              <p className="mt-2 max-w-xl text-sm text-white/80">
                WorkPulse AI is watching, thinking, and acting — tracking your work, scoring your
                focus, and preparing tonight's report, all running locally.
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-5 rounded-xl bg-white/10 p-4 backdrop-blur-sm">
              <div className="text-center">
                <p className="text-theme-xs font-medium uppercase tracking-wide text-white/70">Focus</p>
                <p className="text-3xl font-bold leading-tight">
                  {focusScore != null ? Math.round(focusScore) : "—"}
                  {focusScore != null && <span className="text-base font-medium text-white/70">%</span>}
                </p>
                {scoreDelta != null ? (
                  <div
                    className={`mt-0.5 flex items-center justify-center gap-1 text-[11px] font-medium ${
                      scoreDelta > 0 ? "text-success-300" : scoreDelta < 0 ? "text-red-200" : "text-white/60"
                    }`}
                  >
                    {scoreDelta > 0 ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : scoreDelta < 0 ? (
                      <TrendingDown className="h-3 w-3" />
                    ) : (
                      <Minus className="h-3 w-3" />
                    )}
                    {scoreDelta === 0 ? "same" : `${Math.abs(Math.round(scoreDelta))} pts`}
                  </div>
                ) : (
                  <p className="mt-0.5 text-[11px] text-white/50">vs yesterday n/a</p>
                )}
              </div>
              <span className="h-12 w-px bg-white/15" />
              <WeeklyTrendSparkline scores={scores} />
            </div>
          </div>
        </div>

        {/* System status — compact, since the header's status dot already
            summarises this; here it's supporting detail per-service. */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <StatusChip
            label="Ollama AI"
            value={statusQuery.data ? (statusQuery.data.ollama.connected ? "Running" : "Offline") : "—"}
            icon={Brain}
            tone={statusQuery.data?.ollama.connected ? "success" : "error"}
            hint={statusQuery.data?.ollama.detail}
            loading={statusQuery.isLoading}
          />
          <StatusChip
            label="Desktop Agent"
            value={statusQuery.data ? (statusQuery.data.agent.connected ? "Running" : "Offline") : "—"}
            icon={Cpu}
            tone={statusQuery.data?.agent.connected ? "success" : "error"}
            hint={statusQuery.data?.agent.detail}
            loading={statusQuery.isLoading}
          />
          <StatusChip
            label="Gmail"
            value={statusQuery.data ? (statusQuery.data.gmail.connected ? "Connected" : "Offline") : "—"}
            icon={Mail}
            tone={statusQuery.data?.gmail.connected ? "success" : "warning"}
            hint={statusQuery.data?.gmail.detail}
            loading={statusQuery.isLoading}
          />
        </div>

        {/* Today's metrics */}
        <div>
          <h2 className="mb-3 text-theme-sm font-semibold text-gray-500 dark:text-gray-400">Today's Metrics</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Active Hours Today"
              value={activeHours}
              icon={Timer}
              hint="Time your system has been on and attended since you started, minus idle"
              loading={scoreQuery.isLoading}
            />
            <StatCard
              label="Idle Time Today"
              value={idleTime}
              icon={Coffee}
              hint="Stretches of 5+ minutes with no keyboard/mouse input"
              loading={scoreQuery.isLoading}
            />
            <StatCard
              label="Work Hours Today"
              value={workHoursValue}
              icon={LogIn}
              hint="Auto-detected from your first/last tracked activity — not a manual clock-in"
              loading={scoreQuery.isLoading}
            />
            <StatCard
              label="Total Apps Tracked"
              value={String(appsTracked)}
              icon={LayoutGrid}
              loading={appsQuery.isLoading}
            />
          </div>
        </div>

        {/* Quick actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {quickActions.map((action) => (
                <QuickActionTile key={action.label} {...action} />
              ))}
            </div>
            {darMessage && (
              <p className="mt-4 text-theme-sm text-gray-500 dark:text-gray-400">{darMessage}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
