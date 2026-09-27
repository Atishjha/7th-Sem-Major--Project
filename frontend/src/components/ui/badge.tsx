import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium tracking-wide",
  {
    variants: {
      tone: {
        neutral: "bg-ink-800 text-slate-300 border border-line",
        signal: "bg-signal/10 text-signal border border-signal/30",
        low: "bg-severity-low/10 text-severity-low border border-severity-low/30",
        medium:
          "bg-severity-medium/10 text-severity-medium border border-severity-medium/30",
        high: "bg-severity-high/10 text-severity-high border border-severity-high/30",
        critical:
          "bg-severity-critical/10 text-severity-critical border border-severity-critical/30",
      },
    },
    defaultVariants: { tone: "neutral" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
