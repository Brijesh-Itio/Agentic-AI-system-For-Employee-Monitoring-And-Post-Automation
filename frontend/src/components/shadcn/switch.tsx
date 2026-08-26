import * as React from "react";
import { cn } from "@/lib/utils";

export type SwitchProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "size">;

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(({ className, disabled, ...props }, ref) => (
  <label
    className={cn(
      "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors",
      "bg-gray-200 has-[:checked]:bg-brand-500 dark:bg-gray-700",
      "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 has-[:focus-visible]:ring-offset-2 dark:has-[:focus-visible]:ring-offset-gray-900",
      disabled && "cursor-not-allowed opacity-50",
      className
    )}
  >
    <input ref={ref} type="checkbox" disabled={disabled} className="peer sr-only" {...props} />
    <span
      aria-hidden
      className="pointer-events-none absolute left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-5"
    />
  </label>
));
Switch.displayName = "Switch";

export { Switch };
