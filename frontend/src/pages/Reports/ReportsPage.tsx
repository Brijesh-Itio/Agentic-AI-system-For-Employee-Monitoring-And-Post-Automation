import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Download, FileText, Loader2, Mail, Sparkles, Zap } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import ScoreGauge from "@/components/Analytics/ScoreGauge";
import ReportsList from "@/components/Reports/ReportsList";
import DarContent from "@/components/Reports/DarContent";
import TaskLog from "@/components/Reports/TaskLog";
import DateSelector from "@/components/Timeline/DateSelector";
import { formatDuration } from "@/components/Timeline/timeScale";
import {
  getAllDars,
  generateDarNow,
  sendDarByDate,
  getLatestWeeklyReport,
} from "@/api";
import { useToast } from "@/context/ToastContext";

type Tab = "daily" | "weekly" | "tasklog";

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>("daily");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [taskLogDate, setTaskLogDate] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const darsQuery = useQuery({ queryKey: ["dar", "all"], queryFn: getAllDars });
  const weeklyQuery = useQuery({
    queryKey: ["weekly", "latest"],
    queryFn: getLatestWeeklyReport,
    retry: false,
  });

  const reports = darsQuery.data ?? [];

  useEffect(() => {
    if (!selectedDate && reports.length > 0) setSelectedDate(reports[0].date);
  }, [reports, selectedDate]);

  const selectedIndex = reports.findIndex((r) => r.date === selectedDate);
  const selectedReport = selectedIndex >= 0 ? reports[selectedIndex] : null;
  // `reports` is newest-first, so the next entry is the closest earlier
  // report — not necessarily literally "yesterday" if a day was skipped.
  const previousReport = selectedIndex >= 0 ? reports[selectedIndex + 1] ?? null : null;

  const generateMutation = useMutation({
    mutationFn: generateDarNow,
    onMutate: () => setStatusMessage("Generating locally with Ollama — this can take a couple of minutes."),
    onSuccess: (report) => {
      setStatusMessage("Report generated.");
      queryClient.invalidateQueries({ queryKey: ["dar", "all"] });
      setSelectedDate(report.date);
      toast.success("DAR generated.");
    },
    onError: () => {
      setStatusMessage("Generation failed — check that Ollama is running.");
      toast.error("Generation failed — check that Ollama is running.");
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => sendDarByDate(selectedDate!),
    onSuccess: () => {
      setStatusMessage("Email sent.");
      queryClient.invalidateQueries({ queryKey: ["dar", "all"] });
      toast.success("Email sent.");
    },
    onError: () => {
      setStatusMessage("Send failed — check Gmail is configured (Module 8).");
      toast.error("Send failed — check Gmail is configured (Module 8).");
    },
  });

  const handleExport = () => {
    if (!selectedReport) return;
    const blob = new Blob([selectedReport.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dar-${selectedReport.date}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageMeta title="Reports | WorkPulse AI" description="AI-generated Daily Activity Reports and weekly summaries." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Reports</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Read AI-generated Daily Activity Reports and weekly summaries.
            </p>
          </div>
          <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate Now
          </Button>
        </div>

        <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5 w-fit">
          <button
            onClick={() => setTab("daily")}
            className={`rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
              tab === "daily" ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
            }`}
          >
            Daily Reports
          </button>
          <button
            onClick={() => setTab("weekly")}
            className={`rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
              tab === "weekly" ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
            }`}
          >
            Weekly Reports
          </button>
          <button
            onClick={() => setTab("tasklog")}
            className={`rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
              tab === "tasklog" ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
            }`}
          >
            Task Log
          </button>
        </div>

        {tab === "daily" ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            <Card className="lg:col-span-1">
              <CardContent className="p-3">
                <ReportsList reports={reports} selectedDate={selectedDate} onSelect={setSelectedDate} />
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardContent className="p-6">
                {darsQuery.isLoading ? (
                  <div className="flex h-40 items-center justify-center text-gray-400">
                    <Loader2 className="h-5 w-5 animate-spin" />
                  </div>
                ) : !selectedReport ? (
                  <div className="flex h-40 flex-col items-center justify-center gap-2 text-center text-theme-sm text-gray-400">
                    <FileText className="h-8 w-8" />
                    No DAR selected yet. Click "Generate Now" to create today's report.
                  </div>
                ) : (
                  <>
                    <div className="mb-5 flex flex-wrap items-center justify-between gap-5 rounded-xl border border-gray-100 bg-gray-50/60 p-4 dark:border-gray-800 dark:bg-white/[0.02]">
                      <div className="flex items-center gap-4">
                        <ScoreGauge
                          score={selectedReport.productivity_score}
                          yesterdayScore={previousReport?.productivity_score ?? null}
                          compareLabel="previous report"
                          size={96}
                        />
                        <div>
                          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            {new Date(`${selectedReport.date}T00:00:00`).toLocaleDateString(undefined, {
                              weekday: "long", month: "long", day: "numeric", year: "numeric",
                            })}
                          </h2>
                          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-theme-xs text-gray-500 dark:text-gray-400">
                            <span className="flex items-center gap-1">
                              <Zap className="h-3.5 w-3.5 text-success-500" />
                              Productive: {formatDuration(selectedReport.productive_seconds)}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5 text-gray-400" />
                              Active: {formatDuration(selectedReport.total_active_seconds)}
                            </span>
                          </div>
                          {selectedReport.emailed_at && (
                            <Badge variant="outline" className="mt-2">
                              Sent
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={handleExport}>
                          <Download className="h-3.5 w-3.5" />
                          Export
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => sendMutation.mutate()}
                          disabled={sendMutation.isPending}
                        >
                          {sendMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
                          {selectedReport.emailed_at ? "Resend" : "Email"}
                        </Button>
                      </div>
                    </div>
                    <DarContent content={selectedReport.content} />
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        ) : tab === "tasklog" ? (
          <Card>
            <CardContent className="p-6">
              <div className="mb-4">
                <DateSelector date={taskLogDate} onChange={setTaskLogDate} />
              </div>
              <TaskLog date={taskLogDate} />
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-6">
              {weeklyQuery.isLoading ? (
                <div className="flex h-40 items-center justify-center text-gray-400">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              ) : weeklyQuery.data ? (
                <DarContent content={weeklyQuery.data.content} />
              ) : (
                <div className="flex h-40 flex-col items-center justify-center gap-2 text-center text-theme-sm text-gray-400">
                  <FileText className="h-8 w-8" />
                  No weekly report available yet.
                  <p className="max-w-sm text-theme-xs">
                    A narrative weekly report generator isn't defined in the build plan yet — module 2.7 computes
                    weekly trend statistics only, not a written summary.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {statusMessage && <p className="text-theme-sm text-gray-500 dark:text-gray-400">{statusMessage}</p>}
      </div>
    </>
  );
}
