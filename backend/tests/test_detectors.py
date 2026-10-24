"""
Rule-based detection (Phase 5), tested rule by rule against hand-built events.
Every test names the behaviour it protects: thresholds, windows, per-source
isolation, debouncing, and runtime configurability.
"""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.detectors.defaults import DEFAULT_RULES
from app.detectors.engine import ensure_default_rules, run_detectors
from app.models.alert import Alert
from app.models.common import Severity
from app.models.detection_rule import DetectionRule
from helpers import failed_login, make_event, now, successful_login


def _rule(db, key) -> DetectionRule:
    return db.scalar(select(DetectionRule).where(DetectionRule.rule_key == key))


def _feed(db, events):
    """Run the engine after each event (as the simulator does); return all alerts."""
    out = []
    for e in events:
        out.extend(run_detectors(db, e))
    return out


# ============================================================ brute force
class TestBruteForce:
    def test_fires_at_threshold_with_evidence(self, db):
        events = [failed_login(db, ip="203.0.113.25") for _ in range(5)]
        alerts = _feed(db, events)
        assert len(alerts) == 1
        a = alerts[0]
        assert a.rule_key == "brute_force"
        assert a.severity == Severity.HIGH
        assert a.source_ip == "203.0.113.25"
        assert a.alert_metadata["failed_count"] == 5
        assert sorted(a.triggering_event_ids) == sorted(e.id for e in events)
        assert a.status == "open"
        assert a.alert_id.startswith("ALT-")

    def test_below_threshold_is_quiet(self, db):
        assert _feed(db, [failed_login(db) for _ in range(4)]) == []

    def test_counts_are_per_source_ip(self, db):
        events = [failed_login(db, ip=f"203.0.113.{i}") for i in range(10, 20)]
        assert _feed(db, events) == []

    def test_successful_logins_do_not_count(self, db):
        events = [failed_login(db) for _ in range(4)] + [successful_login(db, ip="203.0.113.25") for _ in range(5)]
        assert _feed(db, events) == []

    def test_failures_outside_the_window_do_not_add_up(self, db):
        old = now() - timedelta(minutes=30)
        events = [failed_login(db, ts=old + timedelta(seconds=i)) for i in range(4)]
        events += [failed_login(db, ts=now() + timedelta(seconds=i)) for i in range(3)]
        assert _feed(db, events) == []   # 4 old + 3 new, but never 5 within 5 minutes

    def test_burst_is_debounced_to_one_alert(self, db):
        alerts = _feed(db, [failed_login(db) for _ in range(12)])
        assert len(alerts) == 1

    def test_non_login_events_are_ignored(self, db):
        e = make_event(db, source="authentication", event_type="logout", status="failed", source_ip="203.0.113.25")
        assert run_detectors(db, e) == []

    def test_threshold_is_configurable_at_runtime(self, db):
        rule = _rule(db, "brute_force")
        rule.config = {**rule.config, "failed_threshold": 3}
        db.commit()
        assert len(_feed(db, [failed_login(db) for _ in range(3)])) == 1

    def test_disabled_rule_does_not_fire_and_can_be_re_enabled(self, db):
        rule = _rule(db, "brute_force")
        rule.enabled = False
        db.commit()
        assert _feed(db, [failed_login(db) for _ in range(6)]) == []

        rule.enabled = True
        db.commit()
        assert len(_feed(db, [failed_login(db, ip="203.0.113.99") for _ in range(5)])) == 1


# ====================================================== suspicious powershell
class TestSuspiciousPowerShell:
    def _ps(self, db, **meta):
        return make_event(
            db, source="endpoint", event_type="process_execution", hostname="WIN-SRV-WEB01",
            username="demo_user", source_ip="192.168.56.11", metadata=meta,
        )

    def test_flagged_pattern_fires(self, db):
        e = self._ps(db, process="powershell.exe", pattern_matched="hidden_window_flag", command_line="powershell.exe -W Hidden")
        (a,) = run_detectors(db, e)
        assert a.rule_key == "suspicious_powershell"
        assert a.severity == Severity.HIGH
        assert a.hostname == "WIN-SRV-WEB01"
        assert a.alert_metadata["pattern_matched"] == "hidden_window_flag"
        assert a.triggering_event_ids == [e.id]

    def test_plain_powershell_without_pattern_is_ignored(self, db):
        assert run_detectors(db, self._ps(db, process="powershell.exe")) == []

    def test_other_process_with_pattern_is_ignored(self, db):
        assert run_detectors(db, self._ps(db, process="notepad.exe", pattern_matched="hidden_window_flag")) == []

    def test_wrong_event_source_is_ignored(self, db):
        e = make_event(db, source="network", event_type="process_execution",
                       metadata={"process": "powershell.exe", "pattern_matched": "x"})
        assert run_detectors(db, e) == []


# ========================================================= impossible travel
class TestImpossibleTravel:
    def _new_location(self, db, user="demo_user", ts=None):
        return make_event(
            db, source="authentication", event_type="new_location", username=user, ts=ts,
            source_ip="203.0.113.77", hostname="WIN-CLIENT-01",
            metadata={"observed_location": "Lagos (synthetic)", "usual_location": "Bhubaneswar (synthetic)"},
        )

    def test_fires_when_location_changes_right_after_a_login(self, db):
        login = successful_login(db, ts=now() - timedelta(minutes=1))
        loc = self._new_location(db)
        (a,) = run_detectors(db, loc)
        assert a.rule_key == "impossible_travel"
        assert a.severity == Severity.HIGH
        assert a.triggering_event_ids == [login.id, loc.id]
        assert a.alert_metadata["observed_location"] == "Lagos (synthetic)"

    def test_no_prior_login_no_alert(self, db):
        assert run_detectors(db, self._new_location(db)) == []

    def test_prior_login_outside_window_no_alert(self, db):
        successful_login(db, ts=now() - timedelta(minutes=45))
        assert run_detectors(db, self._new_location(db)) == []

    def test_prior_login_must_be_the_same_user(self, db):
        successful_login(db, user="someone_else", ts=now() - timedelta(minutes=1))
        assert run_detectors(db, self._new_location(db, user="demo_user")) == []

    def test_failed_prior_login_does_not_count(self, db):
        failed_login(db, ts=now() - timedelta(minutes=1))
        assert run_detectors(db, self._new_location(db)) == []


# ============================================================= dns anomaly
class TestDnsAnomaly:
    def _dns(self, db, ip="192.168.56.10", ts=None):
        return make_event(db, source="dns", event_type="dns_query", source_ip=ip, ts=ts,
                          hostname="WIN-CLIENT-02", metadata={"domain": "x.invalid"})

    def test_fires_at_query_threshold(self, db):
        base = now()
        alerts = _feed(db, [self._dns(db, ts=base + timedelta(seconds=i)) for i in range(6)])
        assert len(alerts) == 1
        assert alerts[0].rule_key == "dns_anomaly"
        assert alerts[0].severity == Severity.MEDIUM
        assert alerts[0].alert_metadata["query_count"] == 6

    def test_below_threshold_is_quiet(self, db):
        base = now()
        assert _feed(db, [self._dns(db, ts=base + timedelta(seconds=i)) for i in range(5)]) == []

    def test_queries_spread_over_more_than_the_window_are_quiet(self, db):
        base = now() - timedelta(minutes=10)
        events = [self._dns(db, ts=base + timedelta(seconds=90 * i)) for i in range(8)]
        assert _feed(db, events) == []

    def test_counts_are_per_source(self, db):
        base = now()
        events = [self._dns(db, ip=f"192.168.56.{i}", ts=base) for i in range(1, 10)]
        assert _feed(db, events) == []


# ========================================================= abnormal network
class TestAbnormalNetwork:
    def _net(self, db, **meta):
        return make_event(db, source="network", event_type="network_anomaly", source_ip="192.168.56.10",
                          hostname="WIN-CLIENT-01", metadata=meta)

    @pytest.mark.parametrize(
        "meta,severity,trigger",
        [
            ({"unique_destinations": 10}, Severity.MEDIUM, "unique_destinations"),
            ({"unique_destinations": 18}, Severity.MEDIUM, "unique_destinations"),
            ({"bytes_sent": 50_000_000}, Severity.HIGH, "bytes_sent"),
            ({"bytes_sent": 199_999_999}, Severity.HIGH, "bytes_sent"),
            ({"bytes_sent": 200_000_000}, Severity.CRITICAL, "bytes_sent"),
            ({"bytes_sent": 484_577_820}, Severity.CRITICAL, "bytes_sent"),
        ],
    )
    def test_severity_follows_thresholds(self, db, meta, severity, trigger):
        (a,) = run_detectors(db, self._net(db, **meta))
        assert a.rule_key == "abnormal_network"
        assert a.severity == severity
        assert trigger in a.alert_metadata["triggered_by"]

    @pytest.mark.parametrize(
        "meta", [{}, {"unique_destinations": 9}, {"bytes_sent": 49_999_999}, {"unique_destinations": 3, "bytes_sent": 1000}]
    )
    def test_below_thresholds_is_quiet(self, db, meta):
        assert run_detectors(db, self._net(db, **meta)) == []

    def test_both_signals_are_reported_together(self, db):
        (a,) = run_detectors(db, self._net(db, unique_destinations=20, bytes_sent=60_000_000))
        assert set(a.alert_metadata["triggered_by"]) == {"unique_destinations", "bytes_sent"}

    def test_other_event_types_are_ignored(self, db):
        e = make_event(db, source="network", event_type="connection", metadata={"bytes_sent": 10**9})
        assert run_detectors(db, e) == []


# =================================================================== engine
class TestEngine:
    def test_benign_event_produces_nothing(self, db):
        assert run_detectors(db, successful_login(db)) == []
        assert db.query(Alert).count() == 0

    def test_default_rules_are_seeded_once_and_all_enabled(self, db):
        ensure_default_rules(db)
        ensure_default_rules(db)
        rules = db.query(DetectionRule).all()
        assert {r.rule_key for r in rules} == {d["rule_key"] for d in DEFAULT_RULES}
        assert len(rules) == len(DEFAULT_RULES) == 5
        assert all(r.enabled for r in rules)

    def test_reseeding_never_overwrites_an_edited_rule(self, db):
        rule = _rule(db, "brute_force")
        rule.config = {**rule.config, "failed_threshold": 99}
        db.commit()
        ensure_default_rules(db)
        db.expire_all()
        assert _rule(db, "brute_force").config["failed_threshold"] == 99

    def test_every_default_rule_has_a_confidence(self):
        assert all(d["config"].get("confidence") in {"low", "medium", "high"} for d in DEFAULT_RULES)

    def test_rule_without_a_checker_is_skipped_not_fatal(self, db):
        db.add(DetectionRule(rule_key="bogus_rule", name="Bogus", description="no checker", enabled=True, config={}))
        db.commit()
        assert run_detectors(db, successful_login(db)) == []

    def test_one_event_can_trigger_only_matching_rules(self, db):
        events = [failed_login(db) for _ in range(5)]
        alerts = _feed(db, events)
        assert {a.rule_key for a in alerts} == {"brute_force"}
