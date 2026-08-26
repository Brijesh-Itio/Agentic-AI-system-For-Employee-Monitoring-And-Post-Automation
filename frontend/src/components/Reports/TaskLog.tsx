import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileSpreadsheet,
  Loader2,
  Plus,
  Search,
  Settings2,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import DOMPurify from "dompurify";

import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import { useModal } from "@/hooks/useModal";
import DepartmentManagerModal from "./DepartmentManagerModal";
import EntryFormModal from "./EntryFormModal";
import {
  deleteEntry,
  draftEntries,
  exportDarUrl,
  getDepartments,
  getEntriesByDate,
  importDarCsv,
  type DarStatus,
} from "@/api";

const STATUS_META: Record<DarStatus, { label: string; variant: "success" | "warning" | "destructive" | "outline" }> = {
  not_started: { label: "Not Started", variant: "outline" },
  in_progress: { label: "In Progress", variant: "warning" },
  blocked: { label: "Blocked", variant: "destructive" },
  completed: { label: "Completed", variant: "success" },
};

interface TaskLogProps {
  date: string;
}

// Comments come from two sources: the rich text editor (real HTML, already
// constrained to a safe tag set by TipTap's schema) and AI-drafted entries
// (plain text straight from Ollama, which could in principle contain
// characters that look like markup). Sanitizing unconditionally covers
// both without needing to know which one produced a given entry.
function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ["p", "br", "strong", "em", "s", "ul", "ol", "li", "a"],
    ALLOWED_ATTR: ["href", "rel", "target"],
  });
}

function formatClock(iso: string | null, entryDate: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const time = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  // Only show the date when it differs from the entry's own date (e.g. an
  // overnight task that ends after midnight) — otherwise it's just noise.
  const isoDate = iso.slice(0, 10);
  return isoDate === entryDate ? time : `${d.toLocaleDateString(undefined, { month: "short", day: "numeric" })} ${time}`;
}

// "HH:MM" from an entry's start_time, for comparing against the <input
// type="time"> filter values below — both are plain 24h clock strings, so
// a lexical compare is a correct time-of-day compare.
function clockValue(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toTimeString().slice(0, 5);
}

const PAGE_SIZE = 10;

export default function TaskLog({ date }: TaskLogProps) {
  const queryClient = useQueryClient();
  const deptModal = useModal();
  const entryModal = useModal();
  const [draftDeptId, setDraftDeptId] = useState<string>("");
  const [importDeptId, setImportDeptId] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState("");
  const [timeFrom, setTimeFrom] = useState("");
  const [timeTo, setTimeTo] = useState("");
  const [page, setPage] = useState(1);

  const entriesQuery = useQuery({ queryKey: ["dar-entries", date], queryFn: () => getEntriesByDate(date) });
  const deptsQuery = useQuery({ queryKey: ["departments"], queryFn: getDepartments });
  const departments = deptsQuery.data ?? [];
  const allEntries = entriesQuery.data ?? [];

  const deptName = (id: number | null) => departments.find((d) => d.id === id)?.name ?? "—";

  const filteredEntries = useMemo(() => {
    const q = search.trim().toLowerCase();
    return allEntries.filter((entry) => {
      if (q) {
        const haystack = `${entry.task} ${entry.task_description ?? ""} ${entry.project ?? ""} ${deptName(entry.department_id)}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      if (timeFrom || timeTo) {
        const start = clockValue(entry.start_time);
        if (!start) return false;
        if (timeFrom && start < timeFrom) return false;
        if (timeTo && start > timeTo) return false;
      }
      return true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allEntries, search, timeFrom, timeTo, departments]);

  const hasActiveFilters = search.trim() !== "" || timeFrom !== "" || timeTo !== "";
  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const entries = filteredEntries.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const resetFilters = () => {
    setSearch("");
    setTimeFrom("");
    setTimeTo("");
    setPage(1);
  };

  // A new day (or a filter change) invalidates whatever page we were on.
  useEffect(() => setPage(1), [date, search, timeFrom, timeTo]);

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteEntry(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dar-entries", date] }),
  });

  const draftMutation = useMutation({
    mutationFn: (departmentId: number) => draftEntries(date, departmentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dar-entries", date] }),
  });

  const importMutation = useMutation({
    mutationFn: (file: File) => importDarCsv(date, file, importDeptId ? Number(importDeptId) : null),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dar-entries", date] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">Task Log</h3>
          <p className="text-theme-xs text-gray-500 dark:text-gray-400">
            Structured, department-custom entries for {date}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={deptModal.openModal}>
            <Settings2 className="h-3.5 w-3.5" />
            Departments
          </Button>
          <Button size="sm" onClick={entryModal.openModal}>
            <Plus className="h-3.5 w-3.5" />
            Add Entry
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-lg bg-gray-50 p-3 dark:bg-white/5">
        <select
          value={draftDeptId}
          onChange={(e) => setDraftDeptId(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
        >
          <option value="">Choose department to AI-draft…</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <Button
          variant="outline"
          size="sm"
          disabled={!draftDeptId || draftMutation.isPending}
          onClick={() => draftMutation.mutate(Number(draftDeptId))}
        >
          {draftMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          AI Draft
        </Button>
        {draftMutation.isError && (
          <span className="text-xs text-error-500">
            {(draftMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              "Draft failed"}
          </span>
        )}

        <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />

        <a href={exportDarUrl(date, "csv")} target="_blank" rel="noreferrer">
          <Button variant="outline" size="sm">
            <Download className="h-3.5 w-3.5" />
            CSV
          </Button>
        </a>
        <a href={exportDarUrl(date, "docx")} target="_blank" rel="noreferrer">
          <Button variant="outline" size="sm">
            <Download className="h-3.5 w-3.5" />
            DOCX
          </Button>
        </a>
        <a href={exportDarUrl(date, "pdf")} target="_blank" rel="noreferrer">
          <Button variant="outline" size="sm">
            <Download className="h-3.5 w-3.5" />
            PDF
          </Button>
        </a>

        <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" />

        <select
          value={importDeptId}
          onChange={(e) => setImportDeptId(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
        >
          <option value="">Import department (optional)</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) importMutation.mutate(file);
            e.target.value = "";
          }}
        />
        <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={importMutation.isPending}>
          {importMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
          Import CSV
        </Button>
      </div>

      {/* Filter bar: date itself is controlled one level up (the day
          navigator above this component) — this filters *within* that
          day, by task/department text and by time-of-day range. */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-gray-900/40">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search task, description, department…"
            className="w-full rounded-lg border border-gray-200 bg-gray-50 py-1.5 pl-8 pr-3 text-xs text-gray-700 focus:border-brand-400 focus:bg-white focus:outline-none dark:border-gray-700 dark:bg-white/5 dark:text-gray-200 dark:focus:bg-gray-900"
          />
        </div>

        <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <span className="hidden sm:inline">Time</span>
          <input
            type="time"
            value={timeFrom}
            onChange={(e) => setTimeFrom(e.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-2 py-1.5 text-xs text-gray-700 focus:border-brand-400 focus:bg-white focus:outline-none dark:border-gray-700 dark:bg-white/5 dark:text-gray-200"
          />
          <span>–</span>
          <input
            type="time"
            value={timeTo}
            onChange={(e) => setTimeTo(e.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-2 py-1.5 text-xs text-gray-700 focus:border-brand-400 focus:bg-white focus:outline-none dark:border-gray-700 dark:bg-white/5 dark:text-gray-200"
          />
        </div>

        {hasActiveFilters && (
          <button
            onClick={resetFilters}
            className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-white/10 dark:hover:text-gray-200"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}

        <span className="ml-auto text-xs text-gray-400">
          {filteredEntries.length === allEntries.length
            ? `${allEntries.length} ${allEntries.length === 1 ? "entry" : "entries"}`
            : `${filteredEntries.length} of ${allEntries.length} entries`}
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-100 shadow-sm dark:border-gray-800">
        <table className="w-full text-left text-theme-sm">
          <thead className="sticky top-0 z-10 bg-gray-50 text-xs uppercase tracking-wide text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th className="px-3 py-2.5">Task</th>
              <th className="px-3 py-2.5">Project</th>
              <th className="px-3 py-2.5">Department</th>
              <th className="px-3 py-2.5">Time</th>
              <th className="px-3 py-2.5">Comment</th>
              <th className="px-3 py-2.5">Status</th>
              <th className="px-3 py-2.5">Progress</th>
              <th className="px-3 py-2.5">Custom Fields</th>
              <th className="px-3 py-2.5">Source</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {entriesQuery.isLoading ? (
              <tr>
                <td colSpan={10} className="p-6 text-center text-gray-400">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                </td>
              </tr>
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={10} className="p-8 text-center text-gray-400">
                  <div className="flex flex-col items-center gap-2">
                    <FileSpreadsheet className="h-8 w-8" />
                    {allEntries.length === 0 ? (
                      "No task log entries for this date yet."
                    ) : (
                      <>
                        No entries match these filters.{" "}
                        <button onClick={resetFilters} className="text-brand-500 hover:underline">
                          Clear filters
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-t border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-white/5"
                >
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-900 dark:text-white">{entry.task}</div>
                    {entry.task_description && (
                      <div className="text-xs text-gray-400">{entry.task_description}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{entry.project || "—"}</td>
                  <td className="px-3 py-2">{deptName(entry.department_id)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {formatClock(entry.start_time, entry.date)} – {formatClock(entry.end_time, entry.date)}
                  </td>
                  <td className="max-w-xs px-3 py-2">
                    {entry.comment ? (
                      <div
                        className="prose prose-sm line-clamp-3 max-w-none text-xs text-gray-600 dark:text-gray-300"
                        dangerouslySetInnerHTML={{ __html: sanitizeHtml(entry.comment) }}
                      />
                    ) : (
                      <span className="text-xs text-gray-300 dark:text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={STATUS_META[entry.status].variant}>{STATUS_META[entry.status].label}</Badge>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-14 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
                        <div
                          className={`h-full rounded-full ${entry.progress >= 100 ? "bg-success-500" : "bg-brand-500"}`}
                          style={{ width: `${entry.progress}%` }}
                        />
                      </div>
                      <span className="text-theme-xs text-gray-500 dark:text-gray-400">{entry.progress}%</span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(entry.custom_fields).map(([k, v]) => (
                        <Badge key={k} variant="outline">
                          {k}: {String(v)}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={entry.source === "manual" ? "outline" : "default"}>{entry.source}</Badge>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => deleteMutation.mutate(entry.id)}
                      className="text-gray-400 hover:text-error-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {filteredEntries.length > PAGE_SIZE && (
        <div className="flex items-center justify-between gap-3 px-1 text-xs text-gray-500 dark:text-gray-400">
          <span>
            Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredEntries.length)} of{" "}
            {filteredEntries.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              // Keep the pager compact on many pages: first, last, current,
              // and one neighbour on each side; "…" fills any gap.
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
              .map((p, idx, arr) => (
                <span key={p} className="flex items-center gap-1">
                  {idx > 0 && arr[idx - 1] !== p - 1 && <span className="px-1 text-gray-300 dark:text-gray-600">…</span>}
                  <button
                    onClick={() => setPage(p)}
                    className={`flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium ${
                      p === currentPage
                        ? "bg-brand-500 text-white"
                        : "border border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
                    }`}
                  >
                    {p}
                  </button>
                </span>
              ))}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      <DepartmentManagerModal isOpen={deptModal.isOpen} onClose={deptModal.closeModal} />
      <EntryFormModal isOpen={entryModal.isOpen} onClose={entryModal.closeModal} date={date} />
    </div>
  );
}
