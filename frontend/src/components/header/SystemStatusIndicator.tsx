import { useQuery } from "@tanstack/react-query";
import { getStatus } from "@/api";

const REFRESH_INTERVAL_MS = 30_000;

export default function SystemStatusIndicator() {
  const { data, isError } = useQuery({
    queryKey: ["status"],
    queryFn: getStatus,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const allRunning = data
    ? data.ollama.connected && data.agent.connected && data.database.connected
    : false;

  const dotColor = isError || !data ? "bg-gray-300" : allRunning ? "bg-success-500" : "bg-warning-500";
  const label = isError || !data ? "Checking systems…" : allRunning ? "All systems running" : "Attention needed";

  return (
    <div className="hidden items-center gap-3 lg:flex">
      <div className="flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${dotColor} opacity-60`} />
          <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${dotColor}`} />
        </span>
        <span className="text-theme-sm font-medium text-gray-600 dark:text-gray-300">{label}</span>
      </div>
      <span className="h-4 w-px bg-gray-200 dark:bg-gray-700" />
      <span className="text-theme-sm text-gray-500 dark:text-gray-400">{today}</span>
    </div>
  );
}
