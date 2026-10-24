"""MITRE ATT&CK mapping (Phase 11): rules -> real, public technique ids."""

import re

import pytest

from app.detectors.defaults import DEFAULT_RULES
from app.models.detection_rule import DetectionRule
from app.services.mitre_mapping import RULE_TECHNIQUES, aggregate_technique_observations, techniques_for_rules
from helpers import replay_scenario

EXPECTED = {
    "brute_force": ("T1110", "Credential Access"),
    "suspicious_powershell": ("T1059.001", "Execution"),
    "impossible_travel": ("T1078", "Initial Access"),
    "dns_anomaly": ("T1071.004", "Command and Control"),
    "abnormal_network": ("T1041", "Exfiltration"),
}


@pytest.mark.parametrize("rule_key,expected", EXPECTED.items())
def test_each_rule_maps_to_its_documented_technique(rule_key, expected):
    technique_id, tactic = expected
    (t,) = RULE_TECHNIQUES[rule_key]
    assert t["technique_id"] == technique_id and t["tactic"] == tactic


def test_every_default_detection_rule_has_a_mapping():
    assert {r["rule_key"] for r in DEFAULT_RULES} == set(RULE_TECHNIQUES)


def test_technique_ids_have_valid_attack_format():
    for techniques in RULE_TECHNIQUES.values():
        for t in techniques:
            assert re.fullmatch(r"T\d{4}(\.\d{3})?", t["technique_id"])
            assert t["technique_name"] and t["tactic"]


def test_techniques_for_rules_uses_each_rules_configured_confidence(db):
    result = {t["evidence_rule"]: t for t in techniques_for_rules(db, ["brute_force", "dns_anomaly"])}
    assert result["brute_force"]["confidence"] == "high"
    assert result["dns_anomaly"]["confidence"] == "medium"

    rule = db.query(DetectionRule).filter_by(rule_key="brute_force").one()
    rule.config = {**rule.config, "confidence": "low"}
    db.commit()
    assert techniques_for_rules(db, ["brute_force"])[0]["confidence"] == "low"


def test_unknown_or_empty_rule_lists_are_handled(db):
    assert techniques_for_rules(db, []) == []
    assert techniques_for_rules(db, ["not_a_rule"]) == []


def test_coverage_view_lists_every_technique_even_when_nothing_fired(db):
    obs = aggregate_technique_observations(db)
    assert {o["technique_id"] for o in obs} == {t["technique_id"] for ts in RULE_TECHNIQUES.values() for t in ts}
    assert all(o["alert_count"] == 0 and o["first_seen"] is None and o["evidence_alert_ids"] == [] for o in obs)


def test_coverage_view_reports_real_evidence_after_an_attack(db):
    alerts, incidents = replay_scenario(db, "multi_stage")
    obs = {o["technique_id"]: o for o in aggregate_technique_observations(db)}
    assert obs["T1110"]["alert_count"] == 1
    assert obs["T1110"]["evidence_incident_ids"] == [incidents[0].incident_id]
    assert obs["T1110"]["evidence_alert_ids"] == [a.alert_id for a in alerts if a.rule_key == "brute_force"]
    # fired techniques sort ahead of never-fired ones
    counts = [o["alert_count"] for o in aggregate_technique_observations(db)]
    assert counts == sorted(counts, reverse=True)


def test_mitre_api_is_readable_by_a_viewer(client, headers):
    r = client.get("/api/mitre/techniques", headers=headers["viewer"])
    assert r.status_code == 200 and len(r.json()) == 5
