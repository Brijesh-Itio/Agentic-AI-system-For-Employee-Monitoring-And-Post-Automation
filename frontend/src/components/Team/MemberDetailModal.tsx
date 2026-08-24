import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

import { Modal } from "@/components/ui/modal";
import { Badge } from "@/components/shadcn/badge";
import { getMemberActivity, type TeamMemberStatus } from "@/api";
import { formatDuration } from "@/components/Timeline/timeScale";
import { useAuth } from "@/context/AuthContext";
import AdminControls from "./AdminControls";

const todayStr = () => new Date().toISOString().slice(0, 10);

const CATEGORY_VARIANT = {
  productive: "success",
  neutral: "default",
  distraction: "destructive",
  uncategorised: "outline",
} as const;

interface MemberDetailModalProps {
  member: TeamMemberStatus | null;
  onClose: () => void;
}

export default function MemberDetailModal({ member, onClose }: MemberDetailModalProps) {
  const [date, setDate] = useState(todayStr());
  const { isAdmin, user: currentUser } = useAuth();

  const activityQuery = useQuery({
    queryKey: ["team", "member-activity", member?.user.id, date],
    queryFn: () => getMemberActivity(member!.user.id, date),
    enabled: member != null,
  });

  if (!member) return null;

  return (
    <Modal isOpen={member != null} onClose={onClose} className="max-w-2xl p-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{member.user.name}</h3>
          <p className="text-theme-xs text-gray-400">
            {member.user.email ?? member.user.id} · {member.user.role}
          </p>
        </div>
        <input
          type="date"
          value={date}
          max={todayStr()}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-theme-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
        />
      </div>

      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
          <p className="text-theme-xs text-gray-400">Status</p>
          <p className="mt-1 font-semibold capitalize text-gray-900 dark:text-white">{member.status}</p>
        </div>
        <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
          <p className="text-theme-xs text-gray-400">Focus Score</p>
          <p className="mt-1 font-semibold text-gray-900 dark:text-white">
            {member.focus_score != null ? `${Math.round(member.focus_score)}%` : "—"}
          </p>
        </div>
        <div className="rounded-lg border border-gray-100 p-3 dark:border-gray-800">
          <p className="text-theme-xs text-gray-400">Hours Today</p>
          <p className="mt-1 font-semibold text-gray-900 dark:text-white">{member.active_hours_today}h</p>
        </div>
      </div>

      <div className="max-h-80 overflow-y-auto">
        {activityQuery.isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          </div>
        ) : !activityQuery.data || activityQuery.data.length === 0 ? (
          <p className="py-8 text-center text-theme-sm text-gray-400">No tracked activity for this date.</p>
        ) : (
          <table className="w-full text-left text-theme-sm">
            <thead className="text-xs uppercase text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-2 py-2">App</th>
                <th className="px-2 py-2">Time</th>
                <th className="px-2 py-2">Duration</th>
                <th className="px-2 py-2">Category</th>
              </tr>
            </thead>
            <tbody>
              {activityQuery.data.map((entry) => (
                <tr key={entry.id} className="border-t border-gray-100 dark:border-gray-800">
                  <td className="px-2 py-2 truncate max-w-[160px]">{entry.app_name}</td>
                  <td className="px-2 py-2 whitespace-nowrap text-gray-400">
                    {new Date(entry.start_time).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-2 py-2 whitespace-nowrap">
                    {entry.duration_seconds != null ? formatDuration(entry.duration_seconds) : "—"}
                  </td>
                  <td className="px-2 py-2">
                    <Badge variant={CATEGORY_VARIANT[entry.category]}>{entry.category}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {isAdmin && currentUser && (
        <AdminControls user={member.user} currentUserId={currentUser.id} onDeleted={onClose} />
      )}
    </Modal>
  );
}
