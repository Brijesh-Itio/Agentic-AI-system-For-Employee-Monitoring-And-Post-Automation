import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/shadcn/card";
import { Button } from "@/components/shadcn/button";
import { changePassword } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200";

export default function ChangePasswordCard() {
  const { user } = useAuth();
  const toast = useToast();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  const mutation = useMutation({
    mutationFn: () => changePassword(password),
    onSuccess: () => {
      setPassword("");
      setConfirm("");
      toast.success("Password updated.");
    },
    onError: (error) => {
      const detail = axios.isAxiosError(error) ? (error.response?.data as { detail?: string } | undefined)?.detail : null;
      toast.error(detail ?? "Failed to update password.");
    },
  });

  const mismatch = confirm.length > 0 && password !== confirm;

  if (!user) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account & Password</CardTitle>
        <CardDescription>
          Signed in as {user.name} ({user.role}). Change your login password below.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">New Password</label>
          <input
            type="password"
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 6 characters"
          />
        </div>
        <div>
          <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Confirm Password</label>
          <input
            type="password"
            className={inputClass}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Re-enter password"
          />
        </div>
        {mismatch && <p className="text-theme-xs text-error-600 dark:text-error-400">Passwords don't match.</p>}
        <Button
          disabled={password.length < 6 || mismatch || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Update Password
        </Button>
      </CardContent>
    </Card>
  );
}
