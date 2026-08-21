import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Focus, Frown, HeartPulse, Loader2, Users } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/shadcn/card";
import { getAlertPreferences, updateAlertPreference, type AlertType, type AlertPreference } from "@/api";

const ALERT_META: Record<AlertType, { label: string; description: string; icon: typeof Focus; disabled?: boolean }> = {
  focus: {
    label: "Focus Alert",
    description: "Notify when idle for 30+ minutes during work hours.",
    icon: Focus,
  },
  distraction: {
    label: "Distraction Alert",
    description: "Notify when 30%+ of an hour is spent on distraction apps or sites.",
    icon: Frown,
  },
  wellbeing: {
    label: "Wellbeing Alert",
    description: "Notify on overwork (10+ active hours) or burnout risk (5 consecutive days).",
    icon: HeartPulse,
  },
  manager: {
    label: "Manager Alert",
    description: "Notify managers when a team member is inactive for 2+ hours. Requires Module 21 (Team Intelligence), not built yet.",
    icon: Users,
    disabled: true,
  },
};

function ToggleSwitch({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        checked ? "bg-brand-500" : "bg-gray-200 dark:bg-gray-700"
      }`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [pendingType, setPendingType] = useState<AlertType | null>(null);

  const prefsQuery = useQuery({ queryKey: ["alerts", "preferences"], queryFn: getAlertPreferences });

  const updateMutation = useMutation({
    mutationFn: ({ type, update }: { type: AlertType; update: AlertPreference }) => updateAlertPreference(type, update),
    onMutate: ({ type }) => setPendingType(type),
    onSettled: () => setPendingType(null),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts", "preferences"] }),
  });

  const prefs = prefsQuery.data;

  return (
    <>
      <PageMeta title="Settings | WorkPulse AI" description="Configure alert thresholds and tracking preferences." />

      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Settings</h1>
          <p className="text-theme-sm text-gray-500 dark:text-gray-400">Configure alert preferences.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Alert Preferences</CardTitle>
            <CardDescription>Enable or disable each Smart Alert type (Module 14).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 pt-0">
            {prefsQuery.isLoading ? (
              <div className="flex h-24 items-center justify-center text-gray-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              (Object.keys(ALERT_META) as AlertType[]).map((type) => {
                const meta = ALERT_META[type];
                const Icon = meta.icon;
                const current = prefs?.[type];
                const isPending = updateMutation.isPending && pendingType === type;
                return (
                  <div
                    key={type}
                    className="flex items-center justify-between gap-4 border-b border-gray-100 py-4 last:border-0 dark:border-gray-800"
                  >
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400">
                        <Icon className="h-4.5 w-4.5" />
                      </span>
                      <div>
                        <p className="text-theme-sm font-medium text-gray-800 dark:text-gray-200">{meta.label}</p>
                        <p className="text-theme-xs text-gray-400">{meta.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin text-gray-400" />}
                      <ToggleSwitch
                        checked={current?.enabled ?? true}
                        disabled={meta.disabled}
                        onChange={(enabled) =>
                          updateMutation.mutate({ type, update: { enabled, threshold_value: current?.threshold_value ?? null } })
                        }
                      />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
