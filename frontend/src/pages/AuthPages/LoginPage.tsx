import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { AlertCircle, Loader2 } from "lucide-react";

import AuthLayout from "./AuthPageLayout";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import PageMeta from "@/components/common/PageMeta";
import { useAuth } from "@/context/AuthContext";
import { createTeamUser, getBootstrapStatus } from "@/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  const bootstrapQuery = useQuery({ queryKey: ["auth", "bootstrap-status"], queryFn: getBootstrapStatus });

  const [userId, setUserId] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  const needsSetup = bootstrapQuery.data?.needs_setup ?? false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (needsSetup) {
        // Bootstrap: the very first account is always created as admin — see api/routes/team.py.
        await createTeamUser({ id: userId.trim(), name: name.trim() || userId.trim(), password });
      }
      await login(userId.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      const status = axios.isAxiosError(err) ? err.response?.status : undefined;
      if (status === undefined) {
        setError("Can't reach the API server — check it's running and VITE_API_URL is correct.");
      } else if (needsSetup) {
        setError(status === 409 ? "That ID is already taken." : "Could not create the admin account.");
      } else {
        setError(status === 401 ? "Incorrect user ID or password." : `Login failed (server returned ${status}).`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (bootstrapQuery.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <AuthLayout>
      <PageMeta title="Sign In | WorkPulse AI" description="Sign in to WorkPulse AI." />
      <div className="flex flex-col flex-1 w-full">
        <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              {needsSetup ? "Create the Admin Account" : "Sign In"}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {needsSetup
                ? "No accounts exist yet — the first account you create is the admin (\"the boss\"), with full access to every employee's data and account controls."
                : "Enter your user ID and password to sign in."}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label>{needsSetup ? "User ID" : "User ID or Email"}</Label>
              <Input
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder={needsSetup ? "e.g. jane.doe" : "e.g. jane.doe or jane@company.com"}
              />
            </div>

            {needsSetup && (
              <div>
                <Label>Full Name</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
              </div>
            )}

            <div>
              <Label>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" />
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </div>
            )}

            <Button className="w-full" disabled={!userId.trim() || !password || isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {needsSetup ? "Create Admin Account" : "Sign In"}
            </Button>
          </form>

          {!needsSetup && (
            <p className="mt-5 text-center text-theme-xs text-gray-400">
              Don't have an account? Ask your admin to add you from the Team page.
            </p>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
