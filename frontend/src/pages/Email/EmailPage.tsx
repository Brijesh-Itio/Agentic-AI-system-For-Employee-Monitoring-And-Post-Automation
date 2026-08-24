import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Loader2, Mail, RefreshCw, Send, Users } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import LeadsPanel from "@/components/Email/LeadsPanel";
import { getCampaignLog, getCampaignStats, runEmailCampaign, runFollowUps } from "@/api";

type Tab = "campaigns" | "leads";

export default function EmailPage() {
  const [tab, setTab] = useState<Tab>("campaigns");
  const queryClient = useQueryClient();

  const statsQuery = useQuery({ queryKey: ["email", "stats"], queryFn: getCampaignStats });
  const logQuery = useQuery({ queryKey: ["email", "log"], queryFn: getCampaignLog });

  const campaignMutation = useMutation({
    mutationFn: () => runEmailCampaign(),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["email"] }),
  });

  const followUpMutation = useMutation({
    mutationFn: () => runFollowUps(),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["email"] }),
  });

  const stats = statsQuery.data;

  return (
    <>
      <PageMeta title="Email | WorkPulse AI" description="RAG-personalised lead outreach campaigns sent via Gmail SMTP." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Email</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Module 19 — RAG-personalised outreach, module 20 leads.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => followUpMutation.mutate()} disabled={followUpMutation.isPending}>
              {followUpMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Run Follow-ups
            </Button>
            <Button onClick={() => campaignMutation.mutate()} disabled={campaignMutation.isPending}>
              {campaignMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Run Campaign
            </Button>
          </div>
        </div>

        {(campaignMutation.isSuccess || followUpMutation.isSuccess) && (
          <div className="rounded-lg border border-success-200 bg-success-50 p-3 text-theme-sm text-success-700 dark:border-success-500/20 dark:bg-success-500/10 dark:text-success-400">
            {campaignMutation.data &&
              `Campaign: ${campaignMutation.data.attempted} attempted, ${campaignMutation.data.sent} sent, ${campaignMutation.data.skipped_unpersonalisable} skipped, ${campaignMutation.data.failed} failed.`}
            {followUpMutation.data &&
              `Follow-ups: ${followUpMutation.data.attempted} attempted, ${followUpMutation.data.sent} sent, ${followUpMutation.data.failed} failed.`}
          </div>
        )}
        {(campaignMutation.isError || followUpMutation.isError) && (
          <div className="flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            Request failed — check the backend is reachable.
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Sent Today</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {stats ? `${stats.sent_today} / ${stats.daily_limit}` : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Total Sent</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_sent ?? "—"}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Total Failed</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_failed ?? "—"}</p>
            </CardContent>
          </Card>
        </div>

        <div className="flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-white/5 w-fit">
          <button
            onClick={() => setTab("campaigns")}
            className={`flex items-center gap-1.5 rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
              tab === "campaigns" ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
            }`}
          >
            <Mail className="h-3.5 w-3.5" />
            Campaign Log
          </button>
          <button
            onClick={() => setTab("leads")}
            className={`flex items-center gap-1.5 rounded-md px-4 py-1.5 text-theme-sm font-medium transition-colors ${
              tab === "leads" ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white" : "text-gray-500"
            }`}
          >
            <Users className="h-3.5 w-3.5" />
            Leads
          </button>
        </div>

        {tab === "campaigns" ? (
          <Card>
            <CardContent className="p-6">
              {logQuery.isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              ) : !logQuery.data || logQuery.data.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-8 text-center text-gray-400">
                  <Mail className="h-8 w-8" />
                  No campaign sends yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-theme-sm">
                    <thead className="text-xs uppercase text-gray-500 dark:text-gray-400">
                      <tr>
                        <th className="px-3 py-2">Date</th>
                        <th className="px-3 py-2">Lead</th>
                        <th className="px-3 py-2">Subject</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2">Follow-up</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logQuery.data.map((entry) => (
                        <tr key={entry.id} className="border-t border-gray-100 dark:border-gray-800">
                          <td className="px-3 py-2 whitespace-nowrap">
                            {entry.date} {entry.time}
                          </td>
                          <td className="px-3 py-2">
                            {entry.name} <span className="text-gray-400">({entry.email})</span>
                          </td>
                          <td className="px-3 py-2">{entry.subject ?? "—"}</td>
                          <td className="px-3 py-2">
                            <Badge variant={entry.status === "sent" ? "success" : "destructive"}>{entry.status}</Badge>
                          </td>
                          <td className="px-3 py-2">{entry.follow_up_sent ? <Badge variant="outline">Sent</Badge> : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-6">
              <LeadsPanel />
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
