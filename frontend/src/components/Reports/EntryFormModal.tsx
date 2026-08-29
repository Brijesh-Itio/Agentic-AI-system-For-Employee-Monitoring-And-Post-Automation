import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, X } from "lucide-react";

import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/shadcn/button";
import { useToast } from "@/context/ToastContext";
import RichTextEditor from "./RichTextEditor";
import {
  createEntry,
  updateEntry,
  getDepartmentTemplate,
  getDepartments,
  type DarEntry,
  type DarEntryInput,
  type DarStatus,
} from "@/api";

interface EntryFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  date: string;
  /** Present => editing that entry (PATCH); absent => creating a new one (POST). */
  entry?: DarEntry | null;
}

// DarEntry stores full ISO timestamps; <input type="datetime-local"> wants
// "YYYY-MM-DDTHH:MM" in local time with no timezone suffix.
function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

const STATUS_OPTIONS: { value: DarStatus; label: string }[] = [
  { value: "not_started", label: "Not Started" },
  { value: "in_progress", label: "In Progress" },
  { value: "blocked", label: "Blocked" },
  { value: "completed", label: "Completed" },
];

export default function EntryFormModal({ isOpen, onClose, date, entry = null }: EntryFormModalProps) {
  const isEditing = entry != null;
  const queryClient = useQueryClient();
  const toast = useToast();
  const [departmentId, setDepartmentId] = useState<number | null>(null);
  const [task, setTask] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [comment, setComment] = useState("");
  const [remarks, setRemarks] = useState("");
  const [link, setLink] = useState("");
  const [project, setProject] = useState("");
  const [status, setStatus] = useState<DarStatus>("in_progress");
  const [progress, setProgress] = useState(0);
  const [customFields, setCustomFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const deptsQuery = useQuery({ queryKey: ["departments"], queryFn: getDepartments, enabled: isOpen });
  const templateQuery = useQuery({
    queryKey: ["dar-template", departmentId],
    queryFn: () => getDepartmentTemplate(departmentId!),
    enabled: isOpen && departmentId != null,
  });

  const reset = () => {
    setDepartmentId(null);
    setTask("");
    setTaskDescription("");
    setStartTime("");
    setEndTime("");
    setComment("");
    setRemarks("");
    setLink("");
    setProject("");
    setStatus("in_progress");
    setProgress(0);
    setCustomFields({});
    setError(null);
  };

  useEffect(() => {
    if (!isOpen) {
      reset();
      return;
    }
    if (entry) {
      setDepartmentId(entry.department_id);
      setTask(entry.task);
      setTaskDescription(entry.task_description ?? "");
      setStartTime(toLocalInput(entry.start_time));
      setEndTime(toLocalInput(entry.end_time));
      setComment(entry.comment ?? "");
      setRemarks(entry.remarks ?? "");
      setLink(entry.link ?? "");
      setProject(entry.project ?? "");
      setStatus(entry.status);
      setProgress(entry.progress);
      setCustomFields(Object.fromEntries(Object.entries(entry.custom_fields).map(([k, v]) => [k, String(v)])));
      setError(null);
    } else {
      setStartTime(`${date}T09:00`);
      setEndTime(`${date}T18:00`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, entry, date]);

  const createMutation = useMutation({
    mutationFn: (payload: DarEntryInput) => createEntry(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dar-entries", date] });
      toast.success("Entry added.");
      onClose();
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create entry";
      setError(detail);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: DarEntryInput) => updateEntry(entry!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dar-entries", date] });
      toast.success("Entry updated.");
      onClose();
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save changes";
      setError(detail);
    },
  });

  const fields = templateQuery.data?.fields ?? [];

  const handleSubmit = () => {
    setError(null);
    const payload: DarEntryInput = {
      date,
      department_id: departmentId,
      task,
      task_description: taskDescription || null,
      start_time: startTime ? `${startTime}:00` : null,
      end_time: endTime ? `${endTime}:00` : null,
      comment: comment || null,
      remarks: remarks || null,
      link: link || null,
      project: project || null,
      status,
      progress,
      custom_fields: customFields,
    };
    if (isEditing) updateMutation.mutate(payload);
    else createMutation.mutate(payload);
  };

  const saving = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-2xl">
      <div className="max-h-[85vh] overflow-y-auto p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {isEditing ? "Edit" : "Add"} Task Log Entry — {date}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Department</label>
            <select
              className={inputClass}
              value={departmentId ?? ""}
              onChange={(e) => {
                setDepartmentId(e.target.value ? Number(e.target.value) : null);
                setCustomFields({});
              }}
            >
              <option value="">No department (base fields only)</option>
              {(deptsQuery.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Task *</label>
            <input className={inputClass} value={task} onChange={(e) => setTask(e.target.value)} />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Project</label>
            <input
              className={inputClass}
              value={project}
              onChange={(e) => setProject(e.target.value)}
              placeholder="e.g. Q3 Revenue Forecasting"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Task Description</label>
            <textarea
              className={inputClass}
              rows={2}
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Start Date & Time</label>
              <input
                type="datetime-local"
                className={inputClass}
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">End Date & Time</label>
              <input
                type="datetime-local"
                className={inputClass}
                min={startTime || undefined}
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Status</label>
              <select
                className={inputClass}
                value={status}
                onChange={(e) => setStatus(e.target.value as DarStatus)}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Progress ({progress}%)</label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                className="w-full accent-brand-500"
                value={progress}
                onChange={(e) => setProgress(Number(e.target.value))}
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Comment</label>
            <RichTextEditor value={comment} onChange={setComment} placeholder="Write a comment…" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Remarks</label>
            <input className={inputClass} value={remarks} onChange={(e) => setRemarks(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Link (if applicable)</label>
            <input className={inputClass} value={link} onChange={(e) => setLink(e.target.value)} />
          </div>

          {departmentId != null && fields.length > 0 && (
            <div className="rounded-lg border border-dashed border-gray-200 p-3 dark:border-gray-800">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                Department Fields
              </p>
              <div className="space-y-3">
                {fields.map((f) => (
                  <div key={f.key}>
                    <label className="mb-1 block text-xs font-medium text-gray-500">
                      {f.label}
                      {f.required && <span className="text-error-500"> *</span>}
                    </label>
                    {f.type === "select" ? (
                      <select
                        className={inputClass}
                        value={customFields[f.key] ?? ""}
                        onChange={(e) => setCustomFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      >
                        <option value="">Select…</option>
                        {(f.options ?? []).map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : f.type === "textarea" ? (
                      <textarea
                        className={inputClass}
                        rows={2}
                        value={customFields[f.key] ?? ""}
                        onChange={(e) => setCustomFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      />
                    ) : (
                      <input
                        type={f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "url" ? "url" : "text"}
                        className={inputClass}
                        value={customFields[f.key] ?? ""}
                        onChange={(e) => setCustomFields((prev) => ({ ...prev, [f.key]: e.target.value }))}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <p className="text-sm text-error-500">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button disabled={!task.trim() || saving} onClick={handleSubmit}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEditing ? "Save Changes" : "Save Entry"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
