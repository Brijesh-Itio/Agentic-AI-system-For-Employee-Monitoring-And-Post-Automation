import type { Category } from "@/api";
import { CATEGORY_COLOR, CATEGORY_LABEL } from "./timeScale";

const CATEGORIES: Category[] = ["productive", "neutral", "distraction", "uncategorised"];

interface CategoryLegendProps {
  active: Category | null;
  onToggle: (category: Category) => void;
}

/** Doubles as a filter — click a category to dim every other one on the
 * track, click again to clear. */
export default function CategoryLegend({ active, onToggle }: CategoryLegendProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {CATEGORIES.map((c) => {
        const isActive = active === c;
        const isDimmed = active !== null && !isActive;
        return (
          <button
            key={c}
            type="button"
            onClick={() => onToggle(c)}
            className={`flex items-center gap-1.5 rounded-full px-2 py-1 text-theme-xs transition-colors ${
              isActive
                ? "bg-gray-100 font-medium text-gray-900 dark:bg-white/10 dark:text-white"
                : "text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-white/5"
            } ${isDimmed ? "opacity-50" : ""}`}
          >
            <span className={`h-2.5 w-2.5 rounded-full ${CATEGORY_COLOR[c]}`} />
            {CATEGORY_LABEL[c]}
          </button>
        );
      })}
    </div>
  );
}
