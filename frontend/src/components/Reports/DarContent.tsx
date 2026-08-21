// Parses the DAR's known 5-section structure (defined by ai/dar_generator.py's
// prompt) into styled blocks, rather than pulling in a full markdown
// renderer for content whose shape is already predictable and fixed.
const SECTION_HEADERS = [
  "Executive Summary",
  "Work Accomplished",
  "Time Analysis",
  "Focus Insights",
  "Tomorrow's Recommendations",
];

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
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.title}>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-brand-600 dark:text-brand-400">
            {section.title}
          </h3>
          <div className="space-y-1.5 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
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
      ))}
    </div>
  );
}
