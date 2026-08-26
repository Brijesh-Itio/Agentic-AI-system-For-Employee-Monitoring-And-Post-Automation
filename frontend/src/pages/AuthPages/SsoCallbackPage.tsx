import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Loader2 } from "lucide-react";

import PageMeta from "@/components/common/PageMeta";
import { useAuth } from "@/context/AuthContext";

// The Google SSO flow (see api/routes/sso.py) redirects the browser here
// with ?token=... once the backend has matched/created the account — this
// page just adopts that token into AuthContext and moves on, same
// destination as a normal password login.
export default function SsoCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const token = searchParams.get("token");
    if (!token) {
      navigate("/login?sso_error=missing_token", { replace: true });
      return;
    }
    loginWithToken(token)
      .then(() => navigate("/", { replace: true }))
      .catch(() => setError("Could not complete sign-in. Please try again."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageMeta title="Signing in… | WorkPulse AI" description="Completing sign-in." />
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-white dark:bg-gray-900">
        {error ? (
          <>
            <p className="text-theme-sm text-error-600 dark:text-error-400">{error}</p>
            <a href="/login" className="text-theme-sm text-brand-500 hover:underline">
              Back to sign in
            </a>
          </>
        ) : (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">Completing sign-in…</p>
          </>
        )}
      </div>
    </>
  );
}
