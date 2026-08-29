import { CheckCircle2 } from "lucide-react";
import type { DarReport } from "@/api";
import { Badge } from "@/components/shadcn/badge";
import ReportTrendSparkline from "./ReportTrendSparkline";

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

const ACCENT_FOR_TONE: Record<ReturnType<typeof scoreTone>, string> = {
  success: "bg-success-400",
  warning: "bg-warning-400",
  destructive: "bg-error-400",
  outline: "bg-gray-200 dark:bg-gray-700",
};

const todayStr = () => new Date().toISOString().slice(0, 10);
function dateLabel(date: string): string {
  if (date === todayStr()) return "Today";
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  if (date === yesterday.toISOString().slice(0, 10)) return "Yesterday";
  return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function ReportsList({ reports, selectedDate, onSelect }: ReportsListProps) {
  if (reports.length === 0) {
    return <p className="px-3 py-6 text-center text-theme-xs text-gray-400">No DARs generated yet</p>;
  }

  return (
    <div>
      <div className="mb-2 px-1">
        <ReportTrendSparkline reports={reports} />
      </div>
      <ul className="flex flex-col gap-1">
        {reports.map((report) => {
          const tone = scoreTone(report.productivity_score);
          const isSelected = selectedDate === report.date;
          return (
            <li key={report.id}>
              <button
                onClick={() => onSelect(report.date)}
                className={`relative flex w-full items-center justify-between overflow-hidden rounded-lg pl-3.5 pr-2.5 py-2.5 text-left text-theme-sm transition-colors ${
                  isSelected
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
                    : "text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
                }`}
              >
                <span className={`absolute inset-y-1 left-0 w-1 rounded-full ${ACCENT_FOR_TONE[tone]}`} />
                <div className="flex items-center gap-2">
                  <span className="font-medium">{dateLabel(report.date)}</span>
                  {report.emailed_at && <CheckCircle2 className="h-3.5 w-3.5 text-success-500" />}
                </div>
                <Badge variant={tone}>
                  {report.productivity_score != null ? `${Math.round(report.productivity_score)}%` : "—"}
                </Badge>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
