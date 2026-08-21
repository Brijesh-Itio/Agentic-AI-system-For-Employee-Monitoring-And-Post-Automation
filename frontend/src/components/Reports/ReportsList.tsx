import { CheckCircle2 } from "lucide-react";
import type { DarReport } from "@/api";
import { Badge } from "@/components/shadcn/badge";

interface ReportsListProps {
  reports: DarReport[];
  selectedDate: string | null;
  onSelect: (date: string) => void;
}

function scoreTone(score: number | null): "success" | "warning" | "destructive" | "outline" {
  if (score == null) return "outline";
  if (score >= 70) return "success";
  if (score >= 40) return "warning";
  return "destructive";
}

export default function ReportsList({ reports, selectedDate, onSelect }: ReportsListProps) {
  if (reports.length === 0) {
    return <p className="px-3 py-6 text-center text-theme-xs text-gray-400">No DARs generated yet</p>;
  }

  return (
    <ul className="flex flex-col gap-1">
      {reports.map((report) => (
        <li key={report.id}>
          <button
            onClick={() => onSelect(report.date)}
            className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-theme-sm transition-colors ${
              selectedDate === report.date
                ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                : "text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
            }`}
          >
            <div className="flex items-center gap-2">
              <span>{new Date(`${report.date}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
              {report.emailed_at && <CheckCircle2 className="h-3.5 w-3.5 text-success-500" />}
            </div>
            <Badge variant={scoreTone(report.productivity_score)}>
              {report.productivity_score != null ? `${Math.round(report.productivity_score)}%` : "—"}
            </Badge>
          </button>
        </li>
      ))}
    </ul>
  );
}
