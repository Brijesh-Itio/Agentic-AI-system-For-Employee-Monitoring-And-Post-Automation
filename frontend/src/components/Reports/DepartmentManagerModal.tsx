import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Trash2, X } from "lucide-react";

import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/shadcn/button";
import { useToast } from "@/context/ToastContext";
import {
  createDepartment,
  deleteDepartment,
  getDepartmentTemplate,
  getDepartments,
  setDepartmentTemplate,
  type FieldDef,
  type FieldType,
} from "@/api";

const FIELD_TYPES: FieldType[] = ["text", "textarea", "number", "date", "select", "url"];

interface DepartmentManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DepartmentManagerModal({ isOpen, onClose }: DepartmentManagerModalProps) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [newDeptName, setNewDeptName] = useState("");
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(null);
  const [fields, setFields] = useState<FieldDef[]>([]);

  const deptsQuery = useQuery({ queryKey: ["departments"], queryFn: getDepartments, enabled: isOpen });
  const departments = deptsQuery.data ?? [];

  const templateQuery = useQuery({
    queryKey: ["dar-template", selectedDeptId],
    queryFn: () => getDepartmentTemplate(selectedDeptId!),
    enabled: isOpen && selectedDeptId != null,
  });

  useEffect(() => {
    if (templateQuery.data) setFields(templateQuery.data.fields);
  }, [templateQuery.data]);

  useEffect(() => {
    if (!isOpen) {
      setSelectedDeptId(null);
      setNewDeptName("");
    }
  }, [isOpen]);

  const createDeptMutation = useMutation({
    mutationFn: (name: string) => createDepartment(name),
    onSuccess: (dept) => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setNewDeptName("");
      setSelectedDeptId(dept.id);
      toast.success(`Department "${dept.name}" created.`);
    },
    onError: () => toast.error("Failed to create department."),
  });

  const deleteDeptMutation = useMutation({
    mutationFn: (id: number) => deleteDepartment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setSelectedDeptId(null);
      toast.success("Department deleted.");
    },
    onError: () => toast.error("Failed to delete department."),
  });

  const saveTemplateMutation = useMutation({
    mutationFn: () => setDepartmentTemplate(selectedDeptId!, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dar-template", selectedDeptId] });
      toast.success("Fields saved.");
    },
    onError: () => toast.error("Failed to save fields."),
  });

  const addField = () => {
    setFields((prev) => [
      ...prev,
      { key: "", label: "", type: "text", required: false, options: null },
    ]);
  };

  const updateField = (index: number, patch: Partial<FieldDef>) => {
    setFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  };

  const removeField = (index: number) => {
    setFields((prev) => prev.filter((_, i) => i !== index));
  };

  const inputClass =
    "rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-3xl">
      <div className="max-h-[85vh] overflow-y-auto p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Manage Departments & DAR Fields</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="md:col-span-1">
            <div className="mb-3 flex gap-2">
              <input
                value={newDeptName}
                onChange={(e) => setNewDeptName(e.target.value)}
                placeholder="New department name"
                className={`${inputClass} flex-1`}
              />
              <Button
                size="sm"
                disabled={!newDeptName.trim() || createDeptMutation.isPending}
                onClick={() => createDeptMutation.mutate(newDeptName.trim())}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            <ul className="space-y-1">
              {departments.map((d) => (
                <li key={d.id}>
                  <button
                    onClick={() => setSelectedDeptId(d.id)}
                    className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm ${
                      selectedDeptId === d.id
                        ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                        : "text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
                    }`}
                  >
                    {d.name}
                    <Trash2
                      className="h-3.5 w-3.5 text-gray-400 hover:text-error-500"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Delete department "${d.name}"? This also removes its template.`)) {
                          deleteDeptMutation.mutate(d.id);
                        }
                      }}
                    />
                  </button>
                </li>
              ))}
              {departments.length === 0 && !deptsQuery.isLoading && (
                <p className="px-3 py-6 text-center text-xs text-gray-400">No departments yet</p>
              )}
            </ul>
          </div>

          <div className="md:col-span-2">
            {selectedDeptId == null ? (
              <div className="flex h-40 items-center justify-center text-sm text-gray-400">
                Select or create a department to edit its custom DAR fields
              </div>
            ) : templateQuery.isLoading ? (
              <div className="flex h-40 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            ) : (
              <div className="space-y-3">
                {fields.map((field, i) => (
                  <div key={i} className="grid grid-cols-12 items-center gap-2 rounded-lg border border-gray-100 p-2 dark:border-gray-800">
                    <input
                      className={`${inputClass} col-span-3`}
                      placeholder="key"
                      value={field.key}
                      onChange={(e) => updateField(i, { key: e.target.value.replace(/\s+/g, "_") })}
                    />
                    <input
                      className={`${inputClass} col-span-3`}
                      placeholder="Label"
                      value={field.label}
                      onChange={(e) => updateField(i, { label: e.target.value })}
                    />
                    <select
                      className={`${inputClass} col-span-2`}
                      value={field.type}
                      onChange={(e) => updateField(i, { type: e.target.value as FieldType })}
                    >
                      {FIELD_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    {field.type === "select" ? (
                      <input
                        className={`${inputClass} col-span-3`}
                        placeholder="opt1,opt2,opt3"
                        value={field.options?.join(",") ?? ""}
                        onChange={(e) =>
                          updateField(i, { options: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })
                        }
                      />
                    ) : (
                      <label className="col-span-3 flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
                        <input
                          type="checkbox"
                          checked={field.required}
                          onChange={(e) => updateField(i, { required: e.target.checked })}
                        />
                        Required
                      </label>
                    )}
                    <button onClick={() => removeField(i)} className="col-span-1 text-gray-400 hover:text-error-500">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}

                <div className="flex items-center justify-between pt-2">
                  <Button variant="outline" size="sm" onClick={addField}>
                    <Plus className="h-3.5 w-3.5" />
                    Add Field
                  </Button>
                  <Button
                    size="sm"
                    disabled={saveTemplateMutation.isPending || fields.some((f) => !f.key || !f.label)}
                    onClick={() => saveTemplateMutation.mutate()}
                  >
                    {saveTemplateMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    Save Fields
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
