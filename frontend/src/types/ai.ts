export interface MitreTechnique {
  tactic: string;
  technique_id: string;
  technique_name: string;
  confidence: string;
  evidence_rule: string;
}

export interface Investigation {
  executive_summary: string;
  what_happened: string;
  timeline_summary: string;
  observed_evidence: string[];
  inference: string[];
  affected_assets: string[];
  indicators: string[];
  mitre_mapping: MitreTechnique[];
  risk_explanation: string;
  recommended_investigation: string[];
  recommended_containment: string[];
  recommended_remediation: string[];
  unknown_information: string[];
  questions_for_analyst: string[];
  generated_by: string;
  generated_at: string;
}
