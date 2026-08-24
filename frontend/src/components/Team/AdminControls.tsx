import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Trash2 } from "lucide-react";

import { Button } from "@/components/shadcn/button";
import { deleteTeamUser, setUserPassword, updateUserRole, type Role, type TeamUser } from "@/api";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

interface AdminControlsProps {
  user: TeamUser;
  currentUserId: string;
  onDeleted: () => void;
}

/** Admin-only ("the boss") account controls: change role, reset/set login
 * password, deactivate the account entirely. Not shown to managers — they
 * get oversight of activity data, not control over accounts. */
export default function AdminControls({ user, currentUserId, onDeleted }: AdminControlsProps) {
  const queryClient = useQueryClient();
  const [role, setRole] = useState<Role>(user.role);
  const [newPassword, setNewPassword] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const roleMutation = useMutation({
    mutationFn: (r: Role) => updateUserRole(user.id, r),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team"] }),
  });

  const passwordMutation = useMutation({
    mutationFn: () => setUserPassword(user.id, newPassword),
    onSuccess: () => {
      setNewPassword("");
      queryClient.invalidateQueries({ queryKey: ["team"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteTeamUser(user.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team"] });
      onDeleted();
    },
  });

  const isSelf = user.id === currentUserId;

  return (
    <div className="mt-4 space-y-4 rounded-lg border border-gray-100 p-4 dark:border-gray-800">
      <p className="text-theme-xs font-medium uppercase tracking-wide text-gray-400">Admin Controls</p>

      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Role</label>
          <select className={inputClass} value={role} onChange={(e) => setRole(e.target.value as Role)}>
            <option value="employee">Employee</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <Button
          variant="outline"
          disabled={role === user.role || roleMutation.isPending}
          onClick={() => roleMutation.mutate(role)}
        >
          {roleMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Save Role
        </Button>
      </div>

      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">
            {user.has_password ? "Reset Password" : "Set Password (no login yet)"}
          </label>
          <input
            type="password"
            className={inputClass}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="At least 6 characters"
          />
        </div>
        <Button
          variant="outline"
          disabled={newPassword.length < 6 || passwordMutation.isPending}
          onClick={() => passwordMutation.mutate()}
        >
          {passwordMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Save
        </Button>
      </div>
      {passwordMutation.isSuccess && (
        <p className="text-theme-xs text-success-600 dark:text-success-400">Password updated.</p>
      )}

      <div className="border-t border-gray-100 pt-3 dark:border-gray-800">
        {isSelf ? (
          <p className="text-theme-xs text-gray-400">You can't delete the account you're logged in as.</p>
        ) : !confirmDelete ? (
          <Button variant="outline" className="text-error-600" onClick={() => setConfirmDelete(true)}>
            <Trash2 className="h-4 w-4" />
            Delete Account
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-theme-xs text-gray-500 dark:text-gray-400">Delete {user.name}'s account?</span>
            <Button
              variant="outline"
              className="text-error-600"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Confirm Delete
            </Button>
            <Button variant="outline" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
