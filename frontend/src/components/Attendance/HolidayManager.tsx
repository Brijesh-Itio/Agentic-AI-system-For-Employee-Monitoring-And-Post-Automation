import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Trash2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/shadcn/card";
import { Button } from "@/components/shadcn/button";
import { Badge } from "@/components/shadcn/badge";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { createHoliday, deleteHoliday, getHolidays, type CompanyHoliday, type HolidayType } from "@/api";

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

/** HR/admin-only holiday declaration panel — every employee (including the
 * rest of the HR team) gets an in-app + email notification the moment
 * something is added here (api/routes/holidays.py's create_holiday). Rendered
 * inline on the Attendance page rather than a separate page, since it's the
 * one place both HR and everyone else already look at the calendar. */
export default function HolidayManager() {
  const { isHr } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [date, setDate] = useState("");
  const [title, setTitle] = useState("");
  const [holidayType, setHolidayType] = useState<HolidayType>("holiday");

  const holidaysQuery = useQuery({
    queryKey: ["holidays", "upcoming"],
    queryFn: () => getHolidays(todayStr()),
    enabled: isHr,
  });

  const createMutation = useMutation({
    mutationFn: () => createHoliday({ date, title: title.trim(), holiday_type: holidayType }),
    onSuccess: (holiday) => {
      setDate("");
      setTitle("");
      setHolidayType("holiday");
      queryClient.invalidateQueries({ queryKey: ["holidays"] });
      queryClient.invalidateQueries({ queryKey: ["attendance"] });
      toast.success(`${holiday.title} added — everyone has been notified.`);
    },
    onError: () => toast.error("Failed to add holiday — it may already exist for that date."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteHoliday(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holidays"] });
      queryClient.invalidateQueries({ queryKey: ["attendance"] });
      toast.success("Holiday removed.");
    },
    onError: () => toast.error("Failed to remove holiday."),
  });

  if (!isHr) return null;

  const holidays: CompanyHoliday[] = holidaysQuery.data ?? [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Manage Holidays</CardTitle>
        <CardDescription>
          HR-only. Every employee — including the rest of the HR team — is notified in-app and by email the moment
          you add one.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
            />
          </div>
          <div className="min-w-[180px] flex-1">
            <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Diwali"
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
            />
          </div>
          <div>
            <label className="mb-1 block text-theme-xs text-gray-500 dark:text-gray-400">Type</label>
            <select
              value={holidayType}
              onChange={(e) => setHolidayType(e.target.value as HolidayType)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
            >
              <option value="holiday">Holiday</option>
              <option value="paid_holiday">Paid Holiday</option>
            </select>
          </div>
          <Button onClick={() => createMutation.mutate()} disabled={!date || !title.trim() || createMutation.isPending}>
            {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add
          </Button>
        </div>

        {holidaysQuery.isLoading ? (
          <div className="flex h-16 items-center justify-center text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : holidays.length === 0 ? (
          <p className="text-theme-sm text-gray-400">No upcoming holidays declared yet.</p>
        ) : (
          <div className="space-y-1.5">
            {holidays.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 px-3 py-2 dark:border-gray-800"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-theme-sm font-medium text-gray-700 dark:text-gray-200">{h.date}</span>
                  <span className="text-theme-sm text-gray-500 dark:text-gray-400">{h.title}</span>
                  <Badge variant={h.holiday_type === "paid_holiday" ? "success" : "outline"}>
                    {h.holiday_type === "paid_holiday" ? "Paid Holiday" : "Holiday"}
                  </Badge>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(h.id)}
                  disabled={deleteMutation.isPending}
                  className="rounded-lg p-1.5 text-gray-400 hover:bg-error-50 hover:text-error-500 dark:hover:bg-error-500/10"
                  aria-label="Delete holiday"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
