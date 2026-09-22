interface ProgressBarProps {
  /**
   * 0-100 for a real, known percentage (e.g. a background job the server
   * reports progress for). Omit it for a long-running action that has no
   * percentage to report — a single blocking request like an Ollama pass or
   * a Playwright session — and the bar animates as "working, no ETA"
   * instead of faking a number.
   */
  value?: number | null;
  /** Red instead of brand color, once the tracked operation has failed. */
  failed?: boolean;
  className?: string;
}

/**
 * A thin progress bar for anything that takes real time. Two modes:
 *   - determinate: pass `value` (0-100) — same look as the live job bars in
 *     Command Mode / LinkedIn, factored out here so every long operation
 *     across the app shares one component.
 *   - indeterminate: omit `value` — an animated sliding segment, for
 *     synchronous requests (audits, AI generation, bulk conversions, ...)
 *     where the server doesn't report a percentage.
 */
export default function ProgressBar({ value, failed = false, className = "" }: ProgressBarProps) {
  const barColor = failed ? "bg-error-500" : "bg-brand-500";
  return (
    <div
      role="progressbar"
      aria-valuenow={value ?? undefined}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-white/10 ${className}`}
    >
      {value == null ? (
        <div className={`h-full w-1/3 animate-progress-indeterminate rounded-full ${barColor}`} />
      ) : (
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      )}
    </div>
  );
}
