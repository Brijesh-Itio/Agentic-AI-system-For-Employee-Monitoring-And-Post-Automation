import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { AlertCircle, KeyRound, Loader2, User, Zap } from "lucide-react";

import AuthLayout from "./AuthPageLayout";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import Button from "@/components/ui/button/Button";
import PageMeta from "@/components/common/PageMeta";
import { useAuth } from "@/context/AuthContext";
import { createTeamUser, getBootstrapStatus, getSsoStatus, googleSsoLoginUrl } from "@/api";

const SSO_ERROR_MESSAGES: Record<string, string> = {
  no_account: "No WorkPulse account found for that Google login — ask your admin to add you from the Team page.",
  unverified_email: "That Google account's email address isn't verified.",
  google_unreachable: "Couldn't reach Google — check your connection and try again.",
  not_configured: "Google sign-in isn't set up yet.",
  invalid_state: "Sign-in session expired — please try again.",
  missing_code: "Sign-in session expired — please try again.",
  missing_token: "Sign-in didn't complete — please try again.",
};

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path
        fill="#4285F4"
        d="M19.6 10.23c0-.68-.06-1.36-.18-2H10v3.79h5.4a4.6 4.6 0 0 1-2 3.02v2.5h3.23c1.9-1.75 3-4.32 3-7.31Z"
      />
      <path
        fill="#34A853"
        d="M10 20c2.7 0 4.96-.89 6.62-2.42l-3.23-2.51c-.9.6-2.05.96-3.39.96-2.6 0-4.8-1.76-5.59-4.12H1.06v2.6A10 10 0 0 0 10 20Z"
      />
      <path
        fill="#FBBC05"
        d="M4.41 11.9a6.02 6.02 0 0 1 0-3.8v-2.6H1.06a10 10 0 0 0 0 9l3.35-2.6Z"
      />
      <path
        fill="#EA4335"
        d="M10 3.98c1.47 0 2.79.5 3.83 1.5l2.87-2.87A9.6 9.6 0 0 0 10 0 10 10 0 0 0 1.06 5.5l3.35 2.6C5.2 5.74 7.4 3.98 10 3.98Z"
      />
    </svg>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, login } = useAuth();
  const bootstrapQuery = useQuery({ queryKey: ["auth", "bootstrap-status"], queryFn: getBootstrapStatus });
  const ssoQuery = useQuery({ queryKey: ["auth", "sso-status"], queryFn: getSsoStatus });

  const [userId, setUserId] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    const ssoError = searchParams.get("sso_error");
    if (ssoError) setError(SSO_ERROR_MESSAGES[ssoError] ?? "Google sign-in failed — please try again.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const needsSetup = bootstrapQuery.data?.needs_setup ?? false;
  const googleEnabled = ssoQuery.data?.google_enabled ?? false;

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
        <div className="animate-auth-fade-up flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
          <Link to="/" className="mb-8 flex items-center gap-2.5 lg:hidden">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-indigo-600 text-white shadow-md shadow-brand-500/30">
              <Zap className="h-5 w-5" fill="currentColor" />
            </span>
            <span className="text-base font-bold tracking-tight text-gray-900 dark:text-white">
              WorkPulse <span className="text-brand-500">AI</span>
            </span>
          </Link>

          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              {needsSetup ? "Create the Admin Account" : "Welcome back"}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {needsSetup
                ? "No accounts exist yet — the first account you create is the admin (\"the boss\"), with full access to every employee's data and account controls."
                : "Enter your user ID and password to sign in."}
            </p>
          </div>

          {googleEnabled && (
            <>
              <a
                href={googleSsoLoginUrl()}
                className="mb-5 flex h-11 w-full items-center justify-center gap-2.5 rounded-lg border border-gray-300 bg-white text-theme-sm font-medium text-gray-700 shadow-theme-xs transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-white/5 dark:text-white/90 dark:hover:bg-white/10"
              >
                <GoogleIcon className="h-4.5 w-4.5" />
                Sign in with Google
              </a>
              <div className="mb-5 flex items-center gap-3">
                <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
                <span className="text-theme-xs text-gray-400">or continue with email</span>
                <span className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label>{needsSetup ? "User ID" : "User ID or Email"}</Label>
              <div className="relative">
                <User className="pointer-events-none absolute left-3.5 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  className="pl-10"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder={needsSetup ? "e.g. jane.doe" : "e.g. jane.doe or jane@company.com"}
                />
              </div>
            </div>

            {needsSetup && (
              <div>
                <Label>Full Name</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
              </div>
            )}

            <div>
              <Label>Password</Label>
              <div className="relative">
                <KeyRound className="pointer-events-none absolute left-3.5 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  className="pl-10"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                />
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-error-200 bg-error-50 p-3 text-theme-sm text-error-700 dark:border-error-500/20 dark:bg-error-500/10 dark:text-error-400">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </div>
            )}

            <Button className="w-full shadow-md shadow-brand-500/20" disabled={!userId.trim() || !password || isSubmitting}>
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
