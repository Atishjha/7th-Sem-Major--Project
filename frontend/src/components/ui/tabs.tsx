import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";
export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...props }: TabsPrimitive.TabsListProps) {
  return (
    <TabsPrimitive.List
      className={cn("flex gap-1 border-b border-line", className)}
      {...props}
    />
  );
}
export function TabsTrigger({ className, ...props }: TabsPrimitive.TabsTriggerProps) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "px-3 py-2 text-sm text-muted border-b-2 border-transparent -mb-px transition-colors",
        "hover:text-slate-200",
        "data-[state=active]:text-slate-100 data-[state=active]:border-signal",
        className
      )}
      {...props}
    />
  );
}
export function TabsContent({ className, ...props }: TabsPrimitive.TabsContentProps) {
  return <TabsPrimitive.Content className={cn("pt-4", className)} {...props} />;
}
