import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Briefcase, Clock, ExternalLink, Loader2, Sparkles } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import { getJobStatus, getLinkedInPosts, getLinkedInStatus, postToLinkedInNow } from "@/api";

export default function LinkedInPage() {
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const statusQuery = useQuery({ queryKey: ["linkedin", "status"], queryFn: getLinkedInStatus });
  const postsQuery = useQuery({ queryKey: ["linkedin", "posts"], queryFn: getLinkedInPosts });

  // Same job system Command Mode uses: the pipeline (write -> generate
  // image -> post) runs for minutes on the server, so this polls live
  // stage progress instead of one long blocking request.
  const jobQuery = useQuery({
    queryKey: ["job", activeJobId],
    queryFn: () => getJobStatus(activeJobId!),
    enabled: activeJobId != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const isDone = status === "completed" || status === "failed" || status === "cancelled";
      if (isDone) queryClient.invalidateQueries({ queryKey: ["linkedin", "status"] });
      if (isDone) queryClient.invalidateQueries({ queryKey: ["linkedin", "posts"] });
      return status === "running" || status === "queued" ? 1_500 : false;
    },
  });

  const postMutation = useMutation({
    mutationFn: () => postToLinkedInNow(topic.trim() || undefined),
    onSuccess: (job) => {
      setActiveJobId(job.id);
      setTopic("");
    },
  });

  const status = statusQuery.data;
  const activeJob = jobQuery.data;
  const isRunning = activeJob?.status === "running" || activeJob?.status === "queued";

  return (
    <>
      <PageMeta title="LinkedIn | WorkPulse AI" description="Autonomous LinkedIn content writing and posting via Playwright." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">LinkedIn</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Module 18 — Ollama-written posts, real Playwright browser automation.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && postMutation.mutate()}
              placeholder="Topic (optional) — e.g. agentic AI in the workplace"
              disabled={postMutation.isPending || isRunning}
              className="w-64 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-700 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
            />
            <Button
              onClick={() => postMutation.mutate()}
              disabled={postMutation.isPending || isRunning || status?.can_post_now === false}
            >
              {postMutation.isPending || isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Post Now
            </Button>
          </div>
        </div>

        {postMutation.isError && (
          <div className="flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {(postMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                "Failed to start"}
            </span>
          </div>
        )}

        {activeJob && (
          <Card>
            <CardContent className="p-6">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-gray-900 dark:text-white">
                  {activeJob.status === "completed"
                    ? "Posted successfully"
                    : activeJob.status === "failed"
                      ? "Post failed"
                      : "Posting to LinkedIn…"}
                </span>
                <Badge
                  variant={
                    activeJob.status === "completed"
                      ? "success"
                      : activeJob.status === "failed"
                        ? "destructive"
                        : "warning"
                  }
                >
                  {activeJob.status}
                </Badge>
              </div>

              <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-white/5">
                <div
                  className={`h-full rounded-full transition-all ${
                    activeJob.status === "failed" ? "bg-error-500" : "bg-brand-500"
                  }`}
                  style={{ width: `${activeJob.progress}%` }}
                />
              </div>

              {/* Live stage log: "Generating post text…" -> "Generating matching image…" -> "Posting to LinkedIn…" */}
              <div className="space-y-1 text-theme-sm text-gray-600 dark:text-gray-300">
                {activeJob.logs.length === 0 ? (
                  <span className="text-gray-400">Starting…</span>
                ) : (
                  activeJob.logs.map((log, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-theme-xs text-gray-400">{new Date(log.at).toLocaleTimeString()}</span>
                      {log.message}
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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Posts Today</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {status ? `${status.posts_today} / ${status.daily_limit}` : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Last Post</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {status?.last_post_at ? new Date(status.last_post_at).toLocaleString() : "Never"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Status</p>
              <div className="mt-1 flex items-center gap-2 text-2xl font-bold text-gray-900 dark:text-white">
                {status?.can_post_now ? (
                  <Badge variant="success">Ready</Badge>
                ) : (
                  <Badge variant="warning">
                    <Clock className="h-3 w-3" />
                    {status?.minutes_until_next_allowed ? `${status.minutes_until_next_allowed}m` : "Limited"}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardContent className="p-6">
            <h2 className="mb-3 text-base font-semibold text-gray-900 dark:text-white">Post History</h2>
            {postsQuery.isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            ) : !postsQuery.data || postsQuery.data.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center text-gray-400">
                <Briefcase className="h-8 w-8" />
                No posts yet.
              </div>
            ) : (
              <div className="space-y-3">
                {postsQuery.data.map((post) => (
                  <div key={post.id} className="rounded-lg border border-gray-100 p-4 dark:border-gray-800">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="text-theme-xs text-gray-400">
                        {post.date} {post.time}
                      </span>
                      <div className="flex items-center gap-2">
                        {post.post_id && (
                          <a
                            href={`https://www.linkedin.com/feed/update/${post.post_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-brand-500 hover:text-brand-600"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                        <Badge variant={post.status === "success" ? "success" : "destructive"}>{post.status}</Badge>
                      </div>
                    </div>
                    <p className="whitespace-pre-wrap text-theme-sm text-gray-700 dark:text-gray-200">{post.content}</p>
                    {post.error && <p className="mt-2 text-theme-xs text-error-500">{post.error}</p>}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
