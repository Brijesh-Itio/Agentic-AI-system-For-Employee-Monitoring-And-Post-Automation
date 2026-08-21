import { ShieldCheck } from "lucide-react";

export default function SidebarWidget() {
  return (
    <div className="mx-auto mb-10 w-full max-w-60 rounded-2xl border border-gray-100 bg-gradient-to-br from-brand-50 to-white px-4 py-5 dark:border-white/5 dark:from-brand-500/10 dark:to-transparent">
      <div className="mb-2 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-brand-500" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">100% Local AI</h3>
      </div>
      <p className="text-theme-xs text-gray-500 dark:text-gray-400">
        Every model runs on your machine via Ollama. No cloud APIs, no per-token cost, no data
        leaving this device.
      </p>
    </div>
  );
}
