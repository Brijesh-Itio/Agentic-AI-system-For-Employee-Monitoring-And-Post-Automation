import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Eye, Loader2, RotateCcw, Save, Send } from "lucide-react";

import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import { useToast } from "@/context/ToastContext";
import {
  getEmailTemplates,
  updateEmailTemplate,
  resetEmailTemplate,
  previewEmailTemplate,
  sendTestEmailTemplate,
} from "@/api";

const textAreaClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

function errorDetail(error: unknown, fallback: string): string {
  return axios.isAxiosError(error) ? (error.response?.data as { detail?: string } | undefined)?.detail ?? fallback : fallback;
}

/** HR/admin-only — every outbound email format (DAR reports, each alert
 * type, holiday announcements) is independently editable here. Campaign
 * emails aren't listed: those are already dynamically RAG-written per lead
 * (module 19), there's no fixed format to template. */
export default function EmailTemplatesPanel() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [preview, setPreview] = useState<{ subject: string; body: string } | null>(null);

  const templatesQuery = useQuery({ queryKey: ["email-templates"], queryFn: getEmailTemplates });
  const templates = templatesQuery.data ?? [];
  const selected = templates.find((t) => t.template_key === selectedKey) ?? null;

  useEffect(() => {
    if (!selectedKey && templates.length > 0) setSelectedKey(templates[0].template_key);
  }, [selectedKey, templates]);

  // Only re-sync the editor when the *selection* changes, not on every
  // background refetch — otherwise a mid-edit refetch would clobber
  // whatever HR is currently typing.
  useEffect(() => {
    if (selected) {
      setSubject(selected.subject);
      setBody(selected.body);
      setPreview(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKey]);

  const saveMutation = useMutation({
    mutationFn: () => updateEmailTemplate(selected!.template_key, subject, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      toast.success("Template saved.");
    },
    onError: (error) => toast.error(errorDetail(error, "Failed to save template.")),
  });

  const resetMutation = useMutation({
    mutationFn: () => resetEmailTemplate(selected!.template_key),
    onSuccess: (tpl) => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setSubject(tpl.subject);
      setBody(tpl.body);
      setPreview(null);
      toast.success("Reset to default.");
    },
    onError: (error) => toast.error(errorDetail(error, "Failed to reset template.")),
  });

  const previewMutation = useMutation({
    mutationFn: () => previewEmailTemplate(selected!.template_key, subject, body),
    onSuccess: (p) => setPreview(p),
    onError: (error) => toast.error(errorDetail(error, "Failed to render preview.")),
  });

  const testMutation = useMutation({
    mutationFn: () => sendTestEmailTemplate(selected!.template_key),
    onSuccess: (r) => toast.success(`Test email sent to ${r.to}.`),
    onError: (error) => toast.error(errorDetail(error, "Failed to send test email.")),
  });

  const isDirty = selected != null && (subject !== selected.subject || body !== selected.body);

  if (templatesQuery.isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-gray-400">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
      <div className="space-y-1 md:col-span-1">
        {templates.map((t) => (
          <button
            key={t.template_key}
            onClick={() => setSelectedKey(t.template_key)}
            className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-theme-sm ${
              t.template_key === selectedKey
                ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                : "text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
            }`}
          >
            {t.label}
            {t.is_custom && (
              <Badge variant="outline" className="ml-2 shrink-0">
                Custom
              </Badge>
            )}
          </button>
        ))}
      </div>

      {selected && (
        <div className="space-y-3 md:col-span-3">
          <p className="text-theme-xs text-gray-400">
            Variables: {selected.variables.split(", ").map((v) => `$${v}`).join(", ")}
            {selected.is_custom && selected.updated_by && (
              <span className="ml-2">— last edited by {selected.updated_by}</span>
            )}
          </p>

          <div>
            <label className="mb-1 block text-theme-xs font-medium text-gray-500 dark:text-gray-400">Subject</label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className={textAreaClass}
            />
          </div>

          <div>
            <label className="mb-1 block text-theme-xs font-medium text-gray-500 dark:text-gray-400">Body</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              className={textAreaClass}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={!isDirty || saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save
            </Button>
            <Button variant="outline" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>
              {previewMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
              Preview
            </Button>
            <Button
              variant="outline"
              onClick={() => resetMutation.mutate()}
              disabled={!selected.is_custom || resetMutation.isPending}
            >
              {resetMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
              Reset to Default
            </Button>
            <Button
              variant="outline"
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
              title="Sends the currently saved version to your own email — save first to test unsaved edits"
            >
              {testMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Send Test
            </Button>
          </div>

          {preview && (
            <div className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 dark:border-gray-800 dark:bg-white/[0.02]">
              <p className="mb-2 text-theme-xs font-semibold uppercase tracking-wide text-gray-400">
                Preview (sample data)
              </p>
              <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{preview.subject}</p>
              <p className="mt-2 whitespace-pre-wrap text-theme-sm text-gray-600 dark:text-gray-300">{preview.body}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
