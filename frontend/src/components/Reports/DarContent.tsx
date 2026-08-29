// Parses the DAR's known 5-section structure (defined by ai/dar_generator.py's
// prompt) into styled blocks, rather than pulling in a full markdown
// renderer for content whose shape is already predictable and fixed.
import type { LucideIcon } from "lucide-react";
import { ClipboardList, Lightbulb, ListChecks, Target, Timer } from "lucide-react";

const SECTION_META: { title: string; icon: LucideIcon; accent: string; iconTone: string }[] = [
  { title: "Executive Summary", icon: ClipboardList, accent: "bg-brand-400", iconTone: "bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400" },
  { title: "Work Accomplished", icon: ListChecks, accent: "bg-success-400", iconTone: "bg-success-50 text-success-600 dark:bg-success-500/10 dark:text-success-400" },
  { title: "Time Analysis", icon: Timer, accent: "bg-indigo-400", iconTone: "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400" },
  { title: "Focus Insights", icon: Target, accent: "bg-warning-400", iconTone: "bg-warning-50 text-warning-600 dark:bg-warning-500/10 dark:text-warning-400" },
  { title: "Tomorrow's Recommendations", icon: Lightbulb, accent: "bg-error-400", iconTone: "bg-error-50 text-error-600 dark:bg-error-500/10 dark:text-error-400" },
];
const SECTION_HEADERS = SECTION_META.map((s) => s.title);

interface Section {
  title: string;
  lines: string[];
}

function parseSections(content: string): Section[] {
  const lines = content.split("\n");
  const sections: Section[] = [];
  let current: Section | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    const headerMatch = SECTION_HEADERS.find(
      (h) => line.replace(/\*\*/g, "").replace(/:$/, "") === h
    );
    if (headerMatch) {
      current = { title: headerMatch, lines: [] };
      sections.push(current);
      continue;
    }
    if (current && line) current.lines.push(line);
  }

  // Fallback: if the model didn't use the exact headers, show it raw
  // rather than silently dropping content.
  if (sections.length === 0) {
    return [{ title: "Report", lines: content.split("\n").filter(Boolean) }];
  }
  return sections;
}

// Minimal inline **bold** support — the small model reliably emits this.
function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="font-semibold text-gray-900 dark:text-white">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export default function DarContent({ content }: { content: string }) {
  const sections = parseSections(content);

  return (
    <div className="space-y-4">
      {sections.map((section) => {
        const meta = SECTION_META.find((m) => m.title === section.title);
        const Icon = meta?.icon ?? ClipboardList;
        return (
          <div
            key={section.title}
            className="relative overflow-hidden rounded-xl border border-gray-100 bg-gray-50/60 pl-4 dark:border-gray-800 dark:bg-white/[0.02]"
          >
            <span className={`absolute inset-y-0 left-0 w-1 ${meta?.accent ?? "bg-brand-400"}`} />
            <div className="p-4 pl-3">
              <div className="mb-2.5 flex items-center gap-2">
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${meta?.iconTone ?? "bg-brand-50 text-brand-600"}`}>
                  <Icon className="h-3.5 w-3.5" />
                </span>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{section.title}</h3>
              </div>
              <div className="space-y-1.5 text-sm leading-relaxed text-gray-600 dark:text-gray-300">
                {section.lines.map((line, i) => {
                  const bulletMatch = line.match(/^[-•]\s*(.*)/);
                  const numberedMatch = line.match(/^\d+\.\s*(.*)/);
                  if (bulletMatch) {
                    return (
                      <div key={i} className="flex gap-2 pl-1">
                        <span className="text-brand-400">•</span>
                        <span>{renderInline(bulletMatch[1])}</span>
                      </div>
                    );
                  }
                  if (numberedMatch) {
                    return (
                      <div key={i} className="flex gap-2 pl-1">
                        <span className="font-medium text-brand-500">{line.match(/^\d+/)?.[0]}.</span>
                        <span>{renderInline(numberedMatch[1])}</span>
                      </div>
                    );
                  }
                  return <p key={i}>{renderInline(line)}</p>;
                })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
