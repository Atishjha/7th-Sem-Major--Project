import type { MitreTechnique } from "@/types/ai";

export interface TechniqueObservation extends MitreTechnique {
  alert_count: number;
  incident_count: number;
  first_seen: string | null;
  last_seen: string | null;
  evidence_alert_ids: string[];
  evidence_incident_ids: string[];
}
