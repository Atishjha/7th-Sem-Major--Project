import * as React from "react";
import { cn } from "@/lib/utils";

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  aside?: React.ReactNode;
}

/**
 * A telemetry-panel container: thin hairline border, corner ticks
 * (a HUD/tactical-display motif appropriate to a SOC console) instead
 * of a rounded card with a drop shadow.
 */
export function Panel({ title, aside, className, children, ...props }: PanelProps) {
  return (
    <div
      className={cn(
        "relative border border-line bg-ink-800/60 rounded-sm",
        className
      )}
      {...props}
    >
      <span className="absolute -top-px -left-px h-2.5 w-2.5 border-t border-l border-signal/60" />
      <span className="absolute -top-px -right-px h-2.5 w-2.5 border-t border-r border-signal/60" />
      <span className="absolute -bottom-px -left-px h-2.5 w-2.5 border-b border-l border-signal/60" />
      <span className="absolute -bottom-px -right-px h-2.5 w-2.5 border-b border-r border-signal/60" />

      {title && (
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h3 className="text-sm font-medium text-slate-200">{title}</h3>
          {aside}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
