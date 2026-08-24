import { Navigate, Outlet } from "react-router";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

/** Wraps the whole app shell — every route under it requires a logged-in user. */
export function ProtectedRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return <Outlet />;
}

/** Wraps individual routes that additionally require manager/admin oversight
 * (e.g. Team). Rendered inside ProtectedRoute, so `user` is always set here. */
export function OversightRoute() {
  const { isOversight } = useAuth();

  if (!isOversight) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-2 text-center">
        <p className="text-lg font-semibold text-gray-900 dark:text-white">Access restricted</p>
        <p className="text-theme-sm text-gray-500 dark:text-gray-400">
          This page is only available to managers and admins.
        </p>
      </div>
    );
  }

  return <Outlet />;
}
