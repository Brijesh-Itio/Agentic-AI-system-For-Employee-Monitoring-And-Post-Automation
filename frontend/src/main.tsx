import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import "swiper/swiper-bundle.css";
import "flatpickr/dist/flatpickr.css";
import App from "./App.tsx";
import { AppWrapper } from "./components/common/PageMeta.tsx";
import { ThemeProvider } from "./context/ThemeContext.tsx";
import { AuthProvider } from "./context/AuthContext.tsx";
import { ToastProvider } from "./context/ToastContext.tsx";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
      // Every page that polls a running job/task (SEO automation history,
      // LinkedIn posting, Command Mode, live dashboard stats, ...) uses
      // `refetchInterval`. TanStack Query's own default for that is to
      // stop polling the moment the browser tab isn't the focused one
      // (document.visibilityState !== "visible") and only resume when the
      // user switches back — the backend work itself was never affected
      // (jobs run in their own background thread, independent of any HTTP
      // connection — see api/routes/command.py and api/routes/linkedin.py),
      // but the UI would sit frozen on whatever it last showed, reading as
      // "the task stopped" even though it hadn't. Setting this true here,
      // once, applies to every current and future `refetchInterval` query
      // in the app — polling keeps running, and the UI stays live, no
      // matter which browser tab is active.
      refetchIntervalInBackground: true,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppWrapper>
          <ToastProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </ToastProvider>
        </AppWrapper>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
