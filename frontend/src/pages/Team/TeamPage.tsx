import { useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { EyeOff, Loader2, UserPlus, Users } from "lucide-react";

import PageMeta from "../../components/common/PageMeta";
import { Button } from "@/components/shadcn/button";
import { Card, CardContent } from "@/components/shadcn/card";
import MemberCard from "@/components/Team/MemberCard";
import AddMemberModal from "@/components/Team/AddMemberModal";
import TeamAnalysisPanel from "@/components/Team/TeamAnalysisPanel";
import { getTeamOverview } from "@/api";
import { useAuth } from "@/context/AuthContext";

export default function TeamPage() {
  const [anonymised, setAnonymised] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const overviewQuery = useQuery({
    queryKey: ["team", "overview"],
    queryFn: getTeamOverview,
    refetchInterval: 60_000, // 21.2 — auto-refresh every 60 seconds
  });

  const members = overviewQuery.data ?? [];

  return (
    <>
      <PageMeta title="Team | WorkPulse AI" description="Manager view of every team member's activity and AI-generated insights." />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Team</h1>
            <p className="text-theme-sm text-gray-500 dark:text-gray-400">
              Module 21 — team overview, individual activity, and AI team analysis.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setAnonymised((v) => !v)}>
              <EyeOff className="h-4 w-4" />
              {anonymised ? "Show Names" : "Anonymise"}
            </Button>
            {isAdmin && (
              <Button onClick={() => setAddOpen(true)}>
                <UserPlus className="h-4 w-4" />
                Add Member
              </Button>
            )}
          </div>
        </div>

        {overviewQuery.isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : members.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-gray-400">
              <Users className="h-8 w-8" />
              No team members registered yet.
              {isAdmin && (
                <Button className="mt-2" onClick={() => setAddOpen(true)}>
                  <UserPlus className="h-4 w-4" />
                  Add Your First Member
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {members.map((m) => (
              <MemberCard
                key={m.user.id}
                member={m}
                anonymised={anonymised}
                onClick={() => navigate(`/team/${m.user.id}`)}
              />
            ))}
          </div>
        )}

        <Card>
          <CardContent className="p-6">
            <TeamAnalysisPanel anonymised={anonymised} />
          </CardContent>
        </Card>
      </div>

      {isAdmin && <AddMemberModal isOpen={addOpen} onClose={() => setAddOpen(false)} />}
    </>
  );
}
