const OPTIONS = [7, 14, 30] as const;

interface PeriodToggleProps {
  value: number;
  onChange: (days: number) => void;
}

export default function PeriodToggle({ value, onChange }: PeriodToggleProps) {
  return (
    <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5 dark:border-gray-800 dark:bg-white/[0.03]">
      {OPTIONS.map((days) => (
        <button
          key={days}
          type="button"
          onClick={() => onChange(days)}
          className={`rounded-md px-2.5 py-1 text-theme-xs font-medium transition-colors ${
            value === days
              ? "bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white"
              : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          }`}
        >
          {days}d
        </button>
      ))}
    </div>
  );
}
