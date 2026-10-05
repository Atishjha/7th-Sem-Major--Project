from datetime import datetime

from pydantic import BaseModel


class MitreTechniqueOut(BaseModel):
    tactic: str
    technique_id: str
    technique_name: str
    confidence: str
    evidence_rule: str


class InvestigationOut(BaseModel):
    """Matches the project spec's AI analyst output list exactly, with
    the four categories the spec requires kept as separate, explicit
    fields rather than inline tags — observed_evidence and inference
    are never merged, recommendations are split by phase, and
    unknown_information says plainly what the data can't tell you."""

    executive_summary: str
    what_happened: str
    timeline_summary: str

    observed_evidence: list[str]
    inference: list[str]

    affected_assets: list[str]
    indicators: list[str]
    mitre_mapping: list[MitreTechniqueOut]

    risk_explanation: str

    recommended_investigation: list[str]
    recommended_containment: list[str]
    recommended_remediation: list[str]

    unknown_information: list[str]
    questions_for_analyst: list[str]

    generated_by: str
    generated_at: datetime

    class Config:
        from_attributes = True
