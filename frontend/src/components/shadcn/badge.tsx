import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300",
        success: "border-transparent bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400",
        warning: "border-transparent bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400",
        destructive: "border-transparent bg-error-50 text-error-700 dark:bg-error-500/15 dark:text-error-400",
        outline: "border-gray-300 text-gray-600 dark:border-gray-700 dark:text-gray-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
