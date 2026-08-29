import type { AttendanceStatus } from "@/api";

export const STATUS_META: Record<
  AttendanceStatus,
  { label: string; variant: "success" | "warning" | "destructive" | "outline" | "default" }
> = {
  full_day: { label: "Full Day", variant: "success" },
  half_day: { label: "Half Day", variant: "warning" },
  absent: { label: "Absent", variant: "destructive" },
  week_off: { label: "Week Off", variant: "outline" },
  upcoming: { label: "Upcoming", variant: "outline" },
};
