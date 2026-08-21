import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing, Focus, Frown, HeartPulse, Users, X } from "lucide-react";
import { Dropdown } from "../ui/dropdown/Dropdown";
import { getAlerts, getUnreadAlertCount, dismissAlert, type Alert, type AlertType } from "@/api";

const REFRESH_INTERVAL_MS = 30_000;

const ALERT_ICON: Record<AlertType, typeof Focus> = {
  focus: Focus,
  distraction: Frown,
  wellbeing: HeartPulse,
  manager: Users,
};

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function NotificationDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const queryClient = useQueryClient();

  const unreadQuery = useQuery({
    queryKey: ["alerts", "unread-count"],
    queryFn: getUnreadAlertCount,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const alertsQuery = useQuery({
    queryKey: ["alerts"],
    queryFn: getAlerts,
    enabled: isOpen,
  });

  const dismissMutation = useMutation({
    mutationFn: dismissAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alerts", "unread-count"] });
    },
  });

  const unreadCount = unreadQuery.data ?? 0;
  const alerts = alertsQuery.data ?? [];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="dropdown-toggle relative flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
        aria-label="Notifications"
      >
        {unreadCount > 0 ? <BellRing className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-error-500 px-1 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <Dropdown isOpen={isOpen} onClose={() => setIsOpen(false)} className="w-80 p-3">
        <div className="mb-2 flex items-center justify-between px-1">
          <h5 className="text-sm font-semibold text-gray-800 dark:text-white/90">Notifications</h5>
          {unreadCount > 0 && <span className="text-theme-xs text-gray-400">{unreadCount} unread</span>}
        </div>

        {alerts.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl bg-gray-50 px-4 py-8 text-center dark:bg-white/[0.03]">
            <Bell className="h-6 w-6 text-gray-300 dark:text-gray-600" />
            <p className="text-sm text-gray-500 dark:text-gray-400">No alerts yet</p>
          </div>
        ) : (
          <ul className="max-h-80 space-y-1 overflow-y-auto">
            {alerts.map((alert: Alert) => {
              const Icon = ALERT_ICON[alert.alert_type] ?? Bell;
              const isUnread = !alert.dismissed_at;
              return (
                <li
                  key={alert.id}
                  className={`flex items-start gap-2.5 rounded-lg p-2.5 ${
                    isUnread ? "bg-brand-50/60 dark:bg-brand-500/5" : ""
                  }`}
                >
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-theme-xs capitalize text-gray-400">{alert.alert_type}</p>
                    <p className="text-theme-sm text-gray-700 dark:text-gray-300">{alert.message}</p>
                    <p className="mt-0.5 text-theme-xs text-gray-400">{relativeTime(alert.triggered_at)}</p>
                  </div>
                  {isUnread && (
                    <button
                      onClick={() => dismissMutation.mutate(alert.id)}
                      className="shrink-0 rounded p-1 text-gray-300 hover:bg-gray-100 hover:text-gray-500 dark:hover:bg-white/10"
                      aria-label="Dismiss"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Dropdown>
    </div>
  );
}
