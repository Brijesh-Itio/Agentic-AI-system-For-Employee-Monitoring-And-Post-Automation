import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Loader2, Plus, Search, Trash2, Users } from "lucide-react";

import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import { createLead, deleteLead, getLeads, runLeadResearch, type LeadInput } from "@/api";

const inputClass =
  "rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

export default function LeadsPanel() {
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [newLead, setNewLead] = useState<LeadInput>({ name: "", company: "", email: "" });
  const [researchQuery, setResearchQuery] = useState("");

  const leadsQuery = useQuery({ queryKey: ["leads"], queryFn: () => getLeads() });

  const createMutation = useMutation({
    mutationFn: (payload: LeadInput) => createLead(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setNewLead({ name: "", company: "", email: "" });
      setShowAddForm(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteLead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["leads"] }),
  });

  const researchMutation = useMutation({
    mutationFn: (targetProfile: string) => runLeadResearch(targetProfile),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["leads"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 rounded-lg bg-gray-50 p-3 dark:bg-white/5">
        <input
          value={researchQuery}
          onChange={(e) => setResearchQuery(e.target.value)}
          placeholder='Target profile, e.g. "AI automation founders"'
          className={`${inputClass} flex-1 min-w-[200px]`}
        />
        <Button
          variant="outline"
          size="sm"
          disabled={!researchQuery.trim() || researchMutation.isPending}
          onClick={() => researchMutation.mutate(researchQuery.trim())}
        >
          {researchMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
          Research Leads
        </Button>
        <Button size="sm" onClick={() => setShowAddForm((v) => !v)}>
          <Plus className="h-3.5 w-3.5" />
          Add Lead
        </Button>
      </div>

      {researchMutation.isError && (
        <div className="flex items-start gap-2 rounded-lg border border-warning-200 bg-warning-50 p-3 text-theme-xs text-warning-700 dark:border-warning-500/20 dark:bg-warning-500/10 dark:text-warning-400">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            {(researchMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              "Research failed"}
          </span>
        </div>
      )}
      {researchMutation.isSuccess && (
        <p className="text-theme-xs text-success-600 dark:text-success-400">
          Found {researchMutation.data.leads_found} lead(s).
        </p>
      )}

      {showAddForm && (
        <div className="grid grid-cols-2 gap-2 rounded-lg border border-dashed border-gray-200 p-3 dark:border-gray-800 sm:grid-cols-5">
          <input className={inputClass} placeholder="Name *" value={newLead.name} onChange={(e) => setNewLead({ ...newLead, name: e.target.value })} />
          <input className={inputClass} placeholder="Company" value={newLead.company ?? ""} onChange={(e) => setNewLead({ ...newLead, company: e.target.value })} />
          <input className={inputClass} placeholder="Role" value={newLead.role ?? ""} onChange={(e) => setNewLead({ ...newLead, role: e.target.value })} />
          <input className={inputClass} placeholder="Email" value={newLead.email ?? ""} onChange={(e) => setNewLead({ ...newLead, email: e.target.value })} />
          <Button size="sm" disabled={!newLead.name.trim() || createMutation.isPending} onClick={() => createMutation.mutate(newLead)}>
            Save
          </Button>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-800">
        <table className="w-full text-left text-theme-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-white/5 dark:text-gray-400">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Company</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {leadsQuery.isLoading ? (
              <tr>
                <td colSpan={6} className="p-6 text-center text-gray-400">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                </td>
              </tr>
            ) : !leadsQuery.data || leadsQuery.data.length === 0 ? (
              <tr>
                <td colSpan={6} className="flex flex-col items-center gap-2 p-8 text-center text-gray-400">
                  <Users className="h-8 w-8" />
                  No leads yet — add one manually or run research.
                </td>
              </tr>
            ) : (
              leadsQuery.data.map((lead) => (
                <tr key={lead.id} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="px-3 py-2 font-medium text-gray-900 dark:text-white">{lead.name}</td>
                  <td className="px-3 py-2">{lead.company ?? "—"}</td>
                  <td className="px-3 py-2">{lead.email ?? "—"}</td>
                  <td className="px-3 py-2">{lead.source ?? "manual"}</td>
                  <td className="px-3 py-2">
                    <Badge variant="outline">{lead.status}</Badge>
                  </td>
                  <td className="px-3 py-2">
                    <button onClick={() => deleteMutation.mutate(lead.id)} className="text-gray-400 hover:text-error-500">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
