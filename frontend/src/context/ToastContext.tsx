import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

type ToastVariant = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const AUTO_DISMISS_MS = 4000;

const VARIANT_META: Record<ToastVariant, { icon: typeof CheckCircle2; classes: string }> = {
  success: {
    icon: CheckCircle2,
    classes:
      "border-success-200 bg-white text-success-700 dark:border-success-500/20 dark:bg-gray-900 dark:text-success-400",
  },
  error: {
    icon: XCircle,
    classes: "border-error-200 bg-white text-error-700 dark:border-error-500/20 dark:bg-gray-900 dark:text-error-400",
  },
  info: {
    icon: Info,
    classes: "border-brand-200 bg-white text-brand-700 dark:border-brand-500/20 dark:bg-gray-900 dark:text-brand-400",
  },
};

/** App-wide toast notifications for one-off feedback (saved, failed,
 * deleted, etc.) — the kind of confirmation a mutation's success/error
 * callback needs but that doesn't belong permanently in the page layout.
 * Mount once at the root (see main.tsx); call via useToast() anywhere
 * beneath it. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string, variant: ToastVariant) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, message, variant }]);
      setTimeout(() => remove(id), AUTO_DISMISS_MS);
    },
    [remove]
  );

  const api = useRef<ToastApi>({
    success: (message) => push(message, "success"),
    error: (message) => push(message, "error"),
    info: (message) => push(message, "info"),
  }).current;

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[9999] flex flex-col items-center gap-2 sm:inset-x-auto sm:right-4 sm:items-end">
        {toasts.map((t) => {
          const meta = VARIANT_META[t.variant];
          const Icon = meta.icon;
          return (
            <div
              key={t.id}
              className={`animate-toast-in pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-lg border px-4 py-3 text-theme-sm shadow-lg ${meta.classes}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" />
              <p className="flex-1">{t.message}</p>
              <button
                onClick={() => remove(t.id)}
                className="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
