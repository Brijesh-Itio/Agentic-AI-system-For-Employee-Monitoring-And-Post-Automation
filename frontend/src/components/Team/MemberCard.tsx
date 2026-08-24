import { Card, CardContent } from "@/components/shadcn/card";
import { Badge } from "@/components/shadcn/badge";
import type { TeamMemberStatus } from "@/api";

const STATUS_VARIANT = {
  active: "success",
  idle: "warning",
  offline: "outline",
} as const;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

interface MemberCardProps {
  member: TeamMemberStatus;
  anonymised: boolean;
  onClick: () => void;
}

export default function MemberCard({ member, anonymised, onClick }: MemberCardProps) {
  const displayName = anonymised ? `Member ${member.user.id.slice(0, 4).toUpperCase()}` : member.user.name;

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-theme-sm font-semibold text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
          {anonymised ? "?" : initials(member.user.name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate font-medium text-gray-900 dark:text-white">{displayName}</p>
            <Badge variant={STATUS_VARIANT[member.status]}>{member.status}</Badge>
          </div>
          <p className="truncate text-theme-xs text-gray-400">
            {member.current_app ?? "No activity today"}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {member.focus_score != null ? `${Math.round(member.focus_score)}%` : "—"}
          </p>
          <p className="text-theme-xs text-gray-400">{member.active_hours_today}h today</p>
        </div>
      </CardContent>
    </Card>
  );
}
