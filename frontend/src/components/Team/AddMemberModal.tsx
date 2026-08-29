import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/shadcn/button";
import { createTeamUser, type Role } from "@/api";
import { useToast } from "@/context/ToastContext";

interface AddMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

export default function AddMemberModal({ isOpen, onClose }: AddMemberModalProps) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("employee");
  const [password, setPassword] = useState("");

  const reset = () => {
    setId("");
    setName("");
    setEmail("");
    setRole("employee");
    setPassword("");
  };

  const mutation = useMutation({
    mutationFn: () => createTeamUser({ id, name, email: email || null, role, password: password || null }),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ["team"] });
      toast.success(`${user.name} added to the team.`);
      reset();
      onClose();
    },
    onError: () => toast.error("Could not add member — check the ID isn't already taken."),
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        reset();
        onClose();
      }}
      className="max-w-md p-6"
    >
      <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Add Team Member</h3>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">
            User ID (they'll log in with this or their email)
          </label>
          <input className={inputClass} value={id} onChange={(e) => setId(e.target.value)} placeholder="e.g. jane.doe" />
        </div>
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Name</label>
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
        </div>
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Email (optional)</label>
          <input className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jane@company.com" />
        </div>
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Role</label>
          <select className={inputClass} value={role} onChange={(e) => setRole(e.target.value as Role)}>
            <option value="employee">Employee</option>
            <option value="manager">Manager</option>
            <option value="hr">HR</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">
            Login Password (optional — they can't sign in until this is set)
          </label>
          <input
            type="password"
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 6 characters"
          />
        </div>
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={() => mutation.mutate()}
          disabled={!id.trim() || !name.trim() || (password.length > 0 && password.length < 6) || mutation.isPending}
        >
          {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Add Member
        </Button>
      </div>
    </Modal>
  );
}
