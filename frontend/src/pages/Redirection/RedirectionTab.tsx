import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Copy,
  ExternalLink,
  Loader2,
  UploadCloud,
  Pencil,
  PlayCircle,
  Route,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import { isAxiosError } from "axios";

import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import { useToast } from "@/context/ToastContext";
import {
  applyRedirect,
  createRedirect,
  deleteRedirect,
  getRedirects,
  testRedirect,
  updateRedirect,
  type RedirectStatusCode,
  type RedirectSyncStatus,
  type RedirectTestResult,
  type UrlRedirect,
} from "@/api";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

const REDIRECT_TYPES: { code: RedirectStatusCode; label: string; hint: string }[] = [
  {
    code: 301,
    label: "Permanent Redirect (301)",
    hint: "Moved for good — browsers and search engines remember it and pass ranking to Url 2.",
  },
  {
    code: 302,
    label: "Temporary Redirect (302)",
    hint: "Moved for now — not cached, search engines keep Url 1 indexed.",
  },
];

/** FastAPI returns `detail` as a string for our own errors, or as a list of
 * field errors for request-shape problems (e.g. a status code other than 301/302). */
function errorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) return detail.map((d) => d.msg).join("; ");
    if (!err.response) return "Can't reach the backend — check that it's running.";
  }
  return "Something went wrong. Please try again.";
}

const SYNC_BADGES: Record<
  RedirectSyncStatus,
  { label: string; variant: "success" | "warning" | "destructive" | "outline" }
> = {
  synced: { label: "Live on site", variant: "success" },
  served: { label: "Served by this API", variant: "outline" },
  pending: { label: "Not applied yet", variant: "warning" },
  unmanaged: { label: "Not live yet", variant: "warning" },
  failed: { label: "Apply failed", variant: "destructive" },
};

/** Result of saving/applying a rule: only "synced"/"served" mean visitors get redirected. */
function outcomeOf(saved: UrlRedirect, verb: string): { ok: boolean; text: string } {
  switch (saved.sync_status) {
    case "synced":
      return { ok: true, text: `Redirect ${verb} and applied on ${saved.apply_site} — verified live. ${saved.sync_message}` };
    case "failed":
      return { ok: false, text: `Redirect saved, but NOT live: ${saved.sync_message}` };
    case "pending":
    case "unmanaged":
      return { ok: false, text: `Redirect saved, but not live yet: ${saved.sync_message}` };
    default:
      return {
        ok: true,
        text: `Redirect ${verb} — ${saved.source_url} now sends visitors to ${saved.target_url} (${saved.status_code}).`,
      };
  }
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "never";
}

/** SEO page tab — global 301/302 redirect rules served by the API (api/routes/redirects.py). */
export default function RedirectionTab() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [sourceUrl, setSourceUrl] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [statusCode, setStatusCode] = useState<RedirectStatusCode>(301);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tests, setTests] = useState<Record<number, RedirectTestResult | "running">>({});
  const [filter, setFilter] = useState("");

  const redirectsQuery = useQuery({ queryKey: ["redirects"], queryFn: getRedirects });

  const resetForm = () => {
    setSourceUrl("");
    setTargetUrl("");
    setStatusCode(301);
    setEditingId(null);
    setFormError(null);
  };

  const dropTestResult = (id: number) =>
    setTests((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = { source_url: sourceUrl.trim(), target_url: targetUrl.trim(), status_code: statusCode };
      return editingId === null ? createRedirect(payload) : updateRedirect(editingId, payload);
    },
    onSuccess: (saved) => {
      const outcome = outcomeOf(saved, editingId === null ? "created" : "updated");
      if (editingId !== null) dropTestResult(editingId);
      resetForm();
      // Saved either way, but only tell the user it's working when it really is.
      if (outcome.ok) {
        setNotice(outcome.text);
        toast.success(outcome.text);
      } else {
        setNotice(null);
        setFormError(outcome.text);
        toast.error(outcome.text);
      }
      queryClient.invalidateQueries({ queryKey: ["redirects"] });
    },
    onError: (err) => {
      setNotice(null);
      setFormError(errorMessage(err));
      toast.error(errorMessage(err));
    },
  });

  const applyMutation = useMutation({
    mutationFn: (id: number) => applyRedirect(id),
    onSuccess: (saved) => {
      const outcome = outcomeOf(saved, "applied");
      if (outcome.ok) toast.success(outcome.text);
      else toast.error(outcome.text);
      dropTestResult(saved.id);
      if (outcome.ok) {
        setFormError(null);
        setNotice(outcome.text);
      } else {
        setNotice(null);
        setFormError(outcome.text);
      }
      queryClient.invalidateQueries({ queryKey: ["redirects"] });
    },
    onError: (err) => {
      setNotice(null);
      setFormError(errorMessage(err));
      toast.error(errorMessage(err));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteRedirect(id),
    onSuccess: (_data, id) => {
      if (editingId === id) resetForm();
      dropTestResult(id);
      setFormError(null);
      setNotice("Redirect deleted.");
      toast.success("Redirect deleted.");
      queryClient.invalidateQueries({ queryKey: ["redirects"] });
    },
    onError: (err) => {
      setNotice(null);
      setFormError(errorMessage(err));
      toast.error(errorMessage(err));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setNotice(null);
    if (!sourceUrl.trim() || !targetUrl.trim()) {
      setFormError("Enter both Url 1 (source) and Url 2 (target).");
      return;
    }
    saveMutation.mutate();
  };

  const startEdit = (row: UrlRedirect) => {
    setEditingId(row.id);
    setSourceUrl(row.source_url);
    setTargetUrl(row.target_url);
    setStatusCode(row.status_code);
    setFormError(null);
    setNotice(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const runTest = async (id: number) => {
    setTests((prev) => ({ ...prev, [id]: "running" }));
    try {
      const result = await testRedirect(id);
      setTests((prev) => ({ ...prev, [id]: result }));
    } catch (err) {
      setTests((prev) => ({
        ...prev,
        [id]: { ok: false, probed_url: "", status_code: null, location: null, message: errorMessage(err) },
      }));
    }
  };

  const copyLive = async (row: UrlRedirect) => {
    try {
      await navigator.clipboard.writeText(row.live_url);
      setFormError(null);
      setNotice(`Copied ${row.live_url}`);
      toast.success("Link copied to clipboard.");
    } catch {
      setNotice(`Copy failed — the link is ${row.live_url}`);
      toast.error("Couldn't copy the link — select it manually.");
    }
  };

  const confirmDelete = (row: UrlRedirect) => {
    if (window.confirm(`Delete the redirect from ${row.source_url}? Visitors will get a 404 again.`)) {
      deleteMutation.mutate(row.id);
    }
  };

  const rows = redirectsQuery.data ?? [];
  const needle = filter.trim().toLowerCase();
  const visible = needle
    ? rows.filter((r) => r.source_url.toLowerCase().includes(needle) || r.target_url.toLowerCase().includes(needle))
    : rows;
  const permanentCount = rows.filter((r) => r.status_code === 301).length;
  const temporaryCount = rows.filter((r) => r.status_code === 302).length;

  return (
    <>
      <div className="space-y-6">
        <p className="text-theme-sm text-gray-500 dark:text-gray-400">
          Send visitors from Url 1 to Url 2 with a permanent (301) or temporary (302) redirect.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Total Redirects</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {redirectsQuery.data ? rows.length : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Permanent (301)</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {redirectsQuery.data ? permanentCount : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-theme-xs text-gray-400">Temporary (302)</p>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                {redirectsQuery.data ? temporaryCount : "—"}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardContent className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                {editingId === null ? "Add a redirect" : `Editing redirect #${editingId}`}
              </h2>
              {editingId !== null && (
                <Button variant="ghost" size="sm" onClick={resetForm} type="button">
                  <X className="h-3.5 w-3.5" />
                  Cancel edit
                </Button>
              )}
            </div>

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div>
                  <label
                    htmlFor="redirect-source"
                    className="mb-1 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                  >
                    Url 1 — redirect from
                  </label>
                  <input
                    id="redirect-source"
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                    placeholder="/old-page  or  https://old.example.com/old-page"
                    className={inputClass}
                    autoComplete="off"
                    spellCheck={false}
                  />
                </div>
                <div>
                  <label
                    htmlFor="redirect-target"
                    className="mb-1 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                  >
                    Url 2 — redirect to
                  </label>
                  <input
                    id="redirect-target"
                    value={targetUrl}
                    onChange={(e) => setTargetUrl(e.target.value)}
                    placeholder="https://example.com/new-page"
                    className={inputClass}
                    autoComplete="off"
                    spellCheck={false}
                  />
                </div>
              </div>

              <fieldset>
                <legend className="mb-1 block text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                  Redirect type
                </legend>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {REDIRECT_TYPES.map((t) => (
                    <label
                      key={t.code}
                      className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                        statusCode === t.code
                          ? "border-brand-500 bg-brand-50 dark:bg-brand-500/10"
                          : "border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-white/5"
                      }`}
                    >
                      <input
                        type="radio"
                        name="redirect-type"
                        value={t.code}
                        checked={statusCode === t.code}
                        onChange={() => setStatusCode(t.code)}
                        className="mt-1 accent-brand-500"
                      />
                      <span>
                        <span className="block text-sm font-medium text-gray-900 dark:text-white">{t.label}</span>
                        <span className="block text-theme-xs text-gray-500 dark:text-gray-400">{t.hint}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <p className="text-theme-xs text-gray-400">
                Url 1 can be a path (answered by this API) or the full URL of a page on your website. For a website
                that has a SEO site with server access (FTP/SFTP), the redirect is written to its{" "}
                <code>.htaccess</code>, checked with a live request, and undone automatically if anything looks
                wrong. Url 2 must be a full http(s) URL.
              </p>

              {formError && (
                <div
                  role="alert"
                  className="flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  {formError}
                </div>
              )}
              {notice && !formError && (
                <div
                  role="status"
                  className="flex items-start gap-2 rounded-lg border border-success-200 bg-success-50 p-3 text-theme-sm text-success-700 dark:border-success-500/20 dark:bg-success-500/10 dark:text-success-400"
                >
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                  <span className="break-all">{notice}</span>
                </div>
              )}

              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {saveMutation.isPending ? "Applying & verifying…" : editingId === null ? "Submit" : "Save changes"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">All redirects</h2>
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Search Url 1 or Url 2…"
                aria-label="Search redirects"
                className={`${inputClass} sm:w-64`}
              />
            </div>

            {redirectsQuery.isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            ) : redirectsQuery.isError ? (
              <div className="flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {errorMessage(redirectsQuery.error)}
              </div>
            ) : visible.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center text-gray-400">
                <Route className="h-8 w-8" />
                {rows.length === 0 ? "No redirects yet — add your first one above." : "No redirects match your search."}
              </div>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-gray-800">
                {visible.map((row) => {
                  const test = tests[row.id];
                  return (
                    <li key={row.id} className="py-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={row.status_code === 301 ? "default" : "warning"}>
                              {row.status_code === 301 ? "301 Permanent" : "302 Temporary"}
                            </Badge>
                            <Badge variant={SYNC_BADGES[row.sync_status].variant}>
                              {SYNC_BADGES[row.sync_status].label}
                            </Badge>
                            {row.sync_status === "served" && (
                              <span className="text-theme-xs text-gray-400">
                                {row.hit_count} {row.hit_count === 1 ? "hit" : "hits"} · last hit{" "}
                                {formatDate(row.last_hit_at)}
                              </span>
                            )}
                          </div>
                          {row.sync_status !== "served" && row.sync_message && (
                            <p className="text-theme-xs text-gray-500 dark:text-gray-400">{row.sync_message}</p>
                          )}
                          <div className="flex flex-wrap items-center gap-2 text-sm">
                            <span className="break-all font-mono text-gray-900 dark:text-white">{row.source_url}</span>
                            <ArrowRight className="h-4 w-4 shrink-0 text-gray-400" />
                            <span className="break-all font-mono text-gray-600 dark:text-gray-300">
                              {row.target_url}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {row.apply_site && (row.sync_status === "pending" || row.sync_status === "failed") && (
                            <Button
                              size="sm"
                              onClick={() => applyMutation.mutate(row.id)}
                              disabled={applyMutation.isPending}
                              title={`Write this redirect into ${row.apply_site}'s .htaccess and verify it`}
                            >
                              {applyMutation.isPending && applyMutation.variables === row.id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <UploadCloud className="h-3.5 w-3.5" />
                              )}
                              Apply to site
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => runTest(row.id)}
                            disabled={test === "running"}
                          >
                            {test === "running" ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <PlayCircle className="h-3.5 w-3.5" />
                            )}
                            Test
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => copyLive(row)}
                            title="Copy the live redirect link"
                          >
                            <Copy className="h-3.5 w-3.5" />
                            Copy link
                          </Button>
                          <Button variant="outline" size="sm" asChild>
                            <a
                              href={row.live_url}
                              target="_blank"
                              rel="noreferrer"
                              title="Open the live redirect in a new tab"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              Open
                            </a>
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => startEdit(row)}>
                            <Pencil className="h-3.5 w-3.5" />
                            Edit
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => confirmDelete(row)}
                            disabled={deleteMutation.isPending && deleteMutation.variables === row.id}
                            className="text-error-600 hover:text-error-700"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </Button>
                        </div>
                      </div>

                      {test && test !== "running" && (
                        <div
                          role="status"
                          className={`mt-3 flex items-start gap-2 rounded-lg border p-3 text-theme-sm ${
                            test.ok
                              ? "border-success-200 bg-success-50 text-success-700 dark:border-success-500/20 dark:bg-success-500/10 dark:text-success-400"
                              : "border-error-200 bg-error-50 text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400"
                          }`}
                        >
                          {test.ok ? (
                            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                          ) : (
                            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                          )}
                          <span className="break-all">{test.message}</span>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
