import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Play, Square, Terminal, XCircle } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import { cancelJob, getJobHistory, getJobStatus, runCommand, type Job } from "@/api";
import { useToast } from "@/context/ToastContext";

const EXAMPLE_COMMANDS = [
  "generate today's report",
  "post to linkedin about agentic AI",
  "run email campaign",
  "find leads for AI startups",
];

function statusBadge(status: Job["status"]) {
  const variant =
    status === "completed" ? "success" : status === "failed" ? "destructive" : status === "cancelled" ? "outline" : "warning";
  return <Badge variant={variant}>{status}</Badge>;
}

export default function CommandModePage() {
  const [command, setCommand] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const activeJobQuery = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: () => getJobStatus(activeJobId!),
    enabled: activeJobId != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "queued" ? 1_500 : false;
    },
  });

  const historyQuery = useQuery({ queryKey: ["job-history"], queryFn: getJobHistory });

  const runMutation = useMutation({
    mutationFn: (cmd: string) => runCommand(cmd),
    onSuccess: (job) => {
      setActiveJobId(job.id);
      setCommand("");
      queryClient.invalidateQueries({ queryKey: ["job-history"] });
    },
    onError: () => toast.error("Failed to start command."),
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => cancelJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", activeJobId] });
      toast.success("Job cancelled.");
    },
    onError: () => toast.error("Failed to cancel job."),
  });

  const activeJob = activeJobQuery.data;
  const isRunning = activeJob?.status === "running" || activeJob?.status === "queued";

  const handleRun = () => {
    if (!command.trim() || runMutation.isPending) return;
    runMutation.mutate(command.trim());
  };

  return (
    <>
      <PageMeta title="Command Mode | WorkPulse AI" description="Type any instruction and the Master Agent executes it." />

      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Command Mode</h1>
          <p className="text-theme-sm text-gray-500 dark:text-gray-400">
            Module 17 — type an instruction, the Master Agent parses and routes it to a real sub-agent.
          </p>
        </div>

        <Card>
          <CardContent className="p-6">
            <div className="flex gap-2">
              <input
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRun()}
                placeholder="e.g. generate today's report, post to linkedin about agentic AI…"
                className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
              />
              <Button onClick={handleRun} disabled={!command.trim() || runMutation.isPending || isRunning}>
                {runMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run
              </Button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {EXAMPLE_COMMANDS.map((ex) => (
                <button
                  key={ex}
                  onClick={() => setCommand(ex)}
                  className="rounded-full border border-gray-200 px-3 py-1 text-theme-xs text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
                >
                  {ex}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {activeJob && (
          <Card>
            <CardContent className="p-6">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 dark:text-white">{activeJob.command}</span>
                  {statusBadge(activeJob.status)}
                  <Badge variant="outline">{activeJob.action}</Badge>
                </div>
                {isRunning && (
                  <Button variant="outline" size="sm" onClick={() => cancelMutation.mutate(activeJob.id)}>
                    <Square className="h-3.5 w-3.5" />
                    Cancel
                  </Button>
                )}
              </div>

              <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-white/5">
                <div
                  className={`h-full rounded-full transition-all ${
                    activeJob.status === "failed" ? "bg-error-500" : "bg-brand-500"
                  }`}
                  style={{ width: `${activeJob.progress}%` }}
                />
              </div>

              <div className="max-h-56 overflow-y-auto rounded-lg bg-gray-900 p-3 font-mono text-theme-xs text-gray-200">
                {activeJob.logs.length === 0 ? (
                  <span className="text-gray-500">Waiting for logs…</span>
                ) : (
                  activeJob.logs.map((log, i) => (
                    <div key={i}>
                      <span className="text-gray-500">{new Date(log.at).toLocaleTimeString()}</span> {log.message}
                    </div>
                  ))
                )}
              </div>

              {activeJob.result && (
                <p className="mt-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  <span className="font-medium">Result:</span> {activeJob.result}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="p-6">
            <h2 className="mb-3 text-base font-semibold text-gray-900 dark:text-white">Job History</h2>
            {historyQuery.isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            ) : !historyQuery.data || historyQuery.data.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center text-gray-400">
                <Terminal className="h-8 w-8" />
                No commands run yet.
              </div>
            ) : (
              <div className="space-y-1">
                {historyQuery.data.map((job) => (
                  <button
                    key={job.id}
                    onClick={() => setActiveJobId(job.id)}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-theme-sm hover:bg-gray-50 dark:hover:bg-white/5"
                  >
                    <div className="flex items-center gap-2 truncate">
                      {job.status === "failed" ? (
                        <XCircle className="h-3.5 w-3.5 shrink-0 text-error-500" />
                      ) : (
                        <Terminal className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                      )}
                      <span className="truncate text-gray-700 dark:text-gray-200">{job.command}</span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {statusBadge(job.status)}
                      <span className="text-theme-xs text-gray-400">
                        {job.created_at && new Date(job.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
