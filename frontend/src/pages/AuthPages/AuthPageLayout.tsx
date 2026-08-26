import React from "react";
import { Link } from "react-router";
import { BarChart3, Camera, FileText, Zap } from "lucide-react";
import ThemeTogglerTwo from "../../components/common/ThemeTogglerTwo";

const FEATURES = [
  { icon: Camera, label: "Automatic screenshot capture" },
  { icon: BarChart3, label: "Live focus & productivity scoring" },
  { icon: FileText, label: "AI-generated daily activity reports" },
];

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative p-6 bg-white z-1 dark:bg-gray-900 sm:p-0">
      <div className="relative flex flex-col justify-center w-full h-screen lg:flex-row dark:bg-gray-900 sm:p-0">
        {children}

        <div className="relative hidden h-full w-full overflow-hidden bg-gradient-to-br from-brand-950 via-[#181b5c] to-indigo-950 lg:flex lg:w-1/2">
          {/* Dot-grid texture */}
          <div
            className="absolute inset-0 opacity-[0.25]"
            style={{
              backgroundImage: "radial-gradient(rgba(255,255,255,0.35) 1px, transparent 1px)",
              backgroundSize: "28px 28px",
            }}
          />

          {/* Floating gradient orbs */}
          <div className="animate-auth-float pointer-events-none absolute -left-16 -top-16 h-72 w-72 rounded-full bg-brand-500/30 blur-3xl" />
          <div
            className="animate-auth-float pointer-events-none absolute -bottom-24 -right-10 h-96 w-96 rounded-full bg-indigo-500/25 blur-3xl"
            style={{ animationDelay: "2s" }}
          />
          <div
            className="animate-auth-float pointer-events-none absolute right-1/4 top-1/3 h-40 w-40 rounded-full bg-brand-400/20 blur-2xl"
            style={{ animationDelay: "4s" }}
          />

          <div className="relative z-10 flex w-full flex-col items-center justify-center px-10">
            <div className="animate-auth-fade-up flex max-w-sm flex-col items-center text-center">
              <span className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-400 to-indigo-500 text-white shadow-lg shadow-brand-500/40 ring-1 ring-white/20">
                <Zap className="h-8 w-8" fill="currentColor" />
              </span>

              <Link to="/" className="mb-3 block text-3xl font-bold tracking-tight text-white">
                WorkPulse <span className="text-brand-300">AI</span>
              </Link>

              <p className="mb-10 text-theme-sm text-white/60">
                Your day at a glance — tracking work, scoring focus, and preparing tonight's report, all running
                locally on your machine.
              </p>

              <div className="w-full space-y-3 text-left">
                {FEATURES.map(({ icon: Icon, label }, i) => (
                  <div
                    key={label}
                    className="animate-auth-fade-up flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm"
                    style={{ animationDelay: `${0.15 * (i + 1)}s` }}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-brand-300">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="text-theme-sm text-white/80">{label}</span>
                  </div>
                ))}
              </div>

              <div
                className="animate-auth-fade-up mt-8 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3.5 py-1.5 text-theme-xs font-medium text-white/70"
                style={{ animationDelay: "0.6s" }}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-success-400" />
                100% Local AI — nothing leaves your device
              </div>
            </div>
          </div>
        </div>

        <div className="fixed z-50 hidden bottom-6 right-6 sm:block">
          <ThemeTogglerTwo />
        </div>
      </div>
    </div>
  );
}
