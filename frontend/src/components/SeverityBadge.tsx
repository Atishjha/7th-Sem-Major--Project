import { Badge } from "@/components/ui/badge";
import type { Severity } from "@/types/event";

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge tone={severity}>{severity}</Badge>;
}
