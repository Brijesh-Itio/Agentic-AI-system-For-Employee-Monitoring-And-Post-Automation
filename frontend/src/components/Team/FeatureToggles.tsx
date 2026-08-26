import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Camera, FileText, type LucideIcon, Loader2, MonitorSmartphone, ShieldCheck } from "lucide-react";

import { getMemberFeatures, setMemberFeature, type FeatureFlag } from "@/api";
import { Switch } from "@/components/shadcn/switch";
import { cn } from "@/lib/utils";

const FEATURES: { id: FeatureFlag; label: string; description: string; icon: LucideIcon }[] = [
  {
    id: "screenshot_capture",
    label: "Screenshot Capture",
    description: "Periodic screen captures from their device",
    icon: Camera,
  },
  {
    id: "activity_tracking",
    label: "App & Website Tracking",
    description: "Which apps and sites they use, and for how long",
    icon: MonitorSmartphone,
  },
  {
    id: "dar_generation",
    label: "Automatic DAR Generation",
    description: "Nightly AI-written Daily Activity Report",
    icon: FileText,
  },
  {
    id: "alerts_enabled",
    label: "Alert Notifications",
    description: "Focus, distraction, and wellbeing email alerts",
    icon: Bell,
  },
];

interface FeatureTogglesProps {
  userId: string;
}

/** Admin-only per-employee monitoring switches. Unlike AdminControls (role/
 * password), these actually stop the corresponding component on the
 * employee's own desktop agent the next time it polls — not just a
 * dashboard-side display toggle. */
export default function FeatureToggles({ userId }: FeatureTogglesProps) {
  const queryClient = useQueryClient();

  const flagsQuery = useQuery({
    queryKey: ["team", "member-features", userId],
    queryFn: () => getMemberFeatures(userId),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ feature, enabled }: { feature: FeatureFlag; enabled: boolean }) =>
      setMemberFeature(userId, feature, enabled),
    onSuccess: (data) => queryClient.setQueryData(["team", "member-features", userId], data),
  });

  const enabledCount = FEATURES.filter((f) => flagsQuery.data?.[f.id] ?? true).length;

  return (
    <div className="mt-4 rounded-xl border border-gray-100 dark:border-gray-800">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-brand-500" />
          <p className="text-theme-sm font-semibold text-gray-900 dark:text-white">Feature Access</p>
        </div>
        {!flagsQuery.isLoading && (
          <span className="text-theme-xs text-gray-400">{enabledCount} of {FEATURES.length} enabled</span>
        )}
      </div>

      {flagsQuery.isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
          {FEATURES.map(({ id, label, description, icon: Icon }) => {
            const enabled = flagsQuery.data?.[id] ?? true;
            const isPending = toggleMutation.isPending && toggleMutation.variables?.feature === id;
            return (
              <div
                key={id}
                className={cn(
                  "flex items-start gap-3 rounded-xl border p-3 transition-colors",
                  enabled
                    ? "border-brand-100 bg-brand-50/40 dark:border-brand-500/20 dark:bg-brand-500/5"
                    : "border-gray-100 bg-gray-50/60 dark:border-gray-800 dark:bg-white/[0.02]"
                )}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                    enabled
                      ? "bg-brand-100 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400"
                      : "bg-gray-200 text-gray-400 dark:bg-white/10 dark:text-gray-500"
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-theme-sm font-medium text-gray-900 dark:text-white">{label}</p>
                  <p className="mt-0.5 text-theme-xs text-gray-400">{description}</p>
                </div>
                <div className="flex shrink-0 items-center pt-0.5">
                  {isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                  ) : (
                    <Switch
                      checked={enabled}
                      disabled={toggleMutation.isPending}
                      onChange={(e) => toggleMutation.mutate({ feature: id, enabled: e.target.checked })}
                      aria-label={label}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
