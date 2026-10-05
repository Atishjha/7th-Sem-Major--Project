"""
MockAIProvider: deterministic, offline, zero-API-key investigation
generator. Every sentence is built from real values pulled out of the
context dict (actual IPs, usernames, counts, timestamps, risk score)
— never a generic placeholder — but the *logic* that assembles them
is template-based rule matching, not a model call. This is what makes
the full demo work with no API key, per the spec's requirement.

Per-rule evidence lines are genuinely derived from each alert's own
metadata (set by the Phase 5 detectors), so a brute_force alert reads
differently from a dns_anomaly alert because the underlying facts are
different, not because of random text variation.
"""

from datetime import datetime, timezone

from app.schemas.ai_investigation import InvestigationOut, MitreTechniqueOut
from app.ai.base import AIProvider


def _evidence_for_alert(a: dict) -> str:
    m = a["metadata"]
    who = a["username"] or a["hostname"] or a["source_ip"] or "an unidentified source"

    if a["rule_key"] == "brute_force":
        return (
            f"{m.get('failed_count', '?')} failed login attempts from "
            f"{a['source_ip']} within {m.get('window_minutes', '?')} minutes, "
            f"targeting {a['username']}."
        )
    if a["rule_key"] == "suspicious_powershell":
        return (
            f"powershell.exe executed on {a['hostname']} matching the "
            f"'{m.get('pattern_matched', 'unknown')}' suspicious pattern "
            f"(command line: {m.get('command_line', 'not captured')})."
        )
    if a["rule_key"] == "impossible_travel":
        return (
            f"{a['username']} logged in successfully, then a login location "
            f"change was observed ({m.get('usual_location', '?')} -> "
            f"{m.get('observed_location', '?')}) {m.get('minutes_since_prior_login', '?')} "
            f"minutes later."
        )
    if a["rule_key"] == "dns_anomaly":
        return (
            f"{m.get('query_count', '?')} DNS queries from {a['source_ip']} within "
            f"{m.get('window_seconds', '?')} seconds, exceeding the configured threshold."
        )
    if a["rule_key"] == "abnormal_network":
        parts = []
        if m.get("bytes_sent"):
            parts.append(f"{m['bytes_sent']:,} bytes sent")
        if m.get("unique_destinations"):
            parts.append(f"{m['unique_destinations']} distinct destinations")
        detail = " and ".join(parts) if parts else "abnormal volume"
        return f"Abnormal outbound network activity from {who}: {detail}."
    return f"{a['rule_name']} triggered for {who}."


NARRATIVES = {
    "account_compromise": {
        "summary": lambda c: (
            f"Account compromise activity for {c['incident']['primary_username'] or 'an unidentified user'} "
            f"from {c['incident']['primary_source_ip'] or 'an unidentified source'}, risk score "
            f"{round(c['incident']['risk_score'] or 0)}/100."
        ),
        "what_happened": lambda c: (
            f"The sequence of {c['incident']['alert_count']} correlated alert(s) is consistent with an "
            f"attacker gaining access to {c['incident']['primary_username'] or 'a user account'}'s "
            f"credentials through repeated login attempts, then operating from an unexpected location."
        ),
    },
    "endpoint_compromise": {
        "summary": lambda c: (
            f"Suspicious endpoint activity on {c['incident']['primary_hostname'] or 'an unidentified host'}, "
            f"risk score {round(c['incident']['risk_score'] or 0)}/100."
        ),
        "what_happened": lambda c: (
            f"A process-execution pattern on {c['incident']['primary_hostname'] or 'the affected host'} "
            f"matches a known suspicious command-line technique, consistent with post-compromise "
            f"tooling or scripted execution rather than routine administrative use."
        ),
    },
    "suspicious_network": {
        "summary": lambda c: (
            f"Suspicious network activity involving {c['incident']['primary_source_ip'] or 'an unidentified host'}, "
            f"risk score {round(c['incident']['risk_score'] or 0)}/100."
        ),
        "what_happened": lambda c: (
            "Both DNS query volume and outbound network volume from the same source exceeded "
            "their configured thresholds in close succession, a pattern associated with "
            "command-and-control beaconing followed by data transfer."
        ),
    },
    "dns_anomaly": {
        "summary": lambda c: (
            f"Anomalous DNS activity from {c['incident']['primary_source_ip'] or 'an unidentified host'}, "
            f"risk score {round(c['incident']['risk_score'] or 0)}/100."
        ),
        "what_happened": lambda c: (
            "DNS query volume and pattern from this source exceeded the configured threshold, "
            "which can indicate domain generation algorithm (DGA) activity, misconfigured "
            "software, or a legitimate but unusually chatty application."
        ),
    },
    "network_anomaly": {
        "summary": lambda c: (
            f"Abnormal network activity from {c['incident']['primary_source_ip'] or 'an unidentified host'}, "
            f"risk score {round(c['incident']['risk_score'] or 0)}/100."
        ),
        "what_happened": lambda c: (
            "Outbound traffic volume or destination diversity from this source exceeded its "
            "configured threshold, which can indicate data exfiltration, a misbehaving "
            "application, or a backup/sync job — the data alone does not distinguish these."
        ),
    },
}

RECOMMENDATIONS = {
    "account_compromise": {
        "investigation": [
            "Review authentication logs for this user across the full retention window, not just this incident's window.",
            "Check whether the same source IP attempted access to other accounts.",
            "Confirm with the user directly whether the observed login location is expected.",
        ],
        "containment": [
            "Force a password reset for the affected account.",
            "Revoke active sessions/tokens for the affected account.",
        ],
        "remediation": [
            "Enable multi-factor authentication for this account if not already required.",
            "Review and tighten login-attempt throttling/lockout policy.",
        ],
    },
    "endpoint_compromise": {
        "investigation": [
            "Inspect the full process tree on the affected host around the time of execution.",
            "Check for persistence mechanisms (scheduled tasks, registry run keys, services) created afterward.",
        ],
        "containment": [
            "Isolate the affected endpoint from the network pending further analysis.",
            "Suspend the user session on the affected host.",
        ],
        "remediation": [
            "Apply PowerShell constrained-language mode or execution-policy restrictions where feasible.",
            "Review endpoint detection coverage for this host class.",
        ],
    },
    "suspicious_network": {
        "investigation": [
            "Capture and inspect full packet data for the flagged destination(s) if still available.",
            "Correlate the destination IPs against external threat-intelligence sources.",
        ],
        "containment": [
            "Block the flagged destination IP(s) at the perimeter firewall.",
            "Isolate the source host pending investigation.",
        ],
        "remediation": [
            "Review egress filtering rules for this network segment.",
        ],
    },
    "dns_anomaly": {
        "investigation": [
            "Review the specific domains queried for known-bad or high-entropy patterns.",
            "Check which process on the host issued the DNS queries.",
        ],
        "containment": [
            "Add the source host to enhanced DNS monitoring.",
        ],
        "remediation": [
            "Consider deploying DNS-layer filtering for this network segment.",
        ],
    },
    "network_anomaly": {
        "investigation": [
            "Identify the process/application responsible for the outbound traffic.",
            "Confirm whether this matches a known scheduled job (backup, sync, replication).",
        ],
        "containment": [
            "Rate-limit or temporarily block outbound traffic from the source host.",
        ],
        "remediation": [
            "Review data-loss-prevention (DLP) coverage for this host class.",
        ],
    },
}


class MockAIProvider(AIProvider):
    name = "mock"

    async def investigate(self, context: dict) -> InvestigationOut:
        inc = context["incident"]
        itype = inc["incident_type"]
        narrative = NARRATIVES.get(itype, NARRATIVES["network_anomaly"])
        recs = RECOMMENDATIONS.get(itype, RECOMMENDATIONS["network_anomaly"])

        observed_evidence = [_evidence_for_alert(a) for a in context["alerts"]]

        inference = [narrative["what_happened"](context)]
        if inc["risk_score"] is not None and inc["risk_score"] >= 75:
            inference.append(
                "The combination of severity, a high-criticality affected asset, and multiple "
                "correlated alerts places this incident in the highest risk band observed by "
                "this system; it warrants prioritized review."
            )

        unknown = [
            "Whether this activity is part of a broader campaign against other accounts or "
            "hosts is unknown without correlating across a wider time window.",
        ]
        if not context["mitre_mapping"]:
            unknown.append("No MITRE ATT&CK techniques are mapped for the rule(s) involved.")

        affected_assets = sorted(
            {inc["primary_hostname"]} - {None}
            | {e["hostname"] for e in context["events"] if e["hostname"]}
        )

        return InvestigationOut(
            executive_summary=narrative["summary"](context),
            what_happened=narrative["what_happened"](context),
            timeline_summary=(
                f"{len(context['events'])} event(s) recorded between {inc['first_seen']} and "
                f"{inc['last_seen']}, generating {inc['alert_count']} alert(s) across "
                f"{len(set(inc['rule_keys']))} detection rule(s)."
            ),
            observed_evidence=observed_evidence,
            inference=inference,
            affected_assets=list(affected_assets) or ["Not determined from available telemetry"],
            indicators=context["indicators"] or ["No source/destination IPs captured"],
            mitre_mapping=[MitreTechniqueOut(**t) for t in context["mitre_mapping"]],
            risk_explanation=(
                f"Risk score {round(inc['risk_score'] or 0)}/100, driven primarily by "
                + ", ".join(
                    f"{f['label']} (+{f['points']})"
                    for f in sorted(
                        inc["risk_breakdown"], key=lambda f: -f["points"]
                    )[:2]
                )
                + "." if inc["risk_breakdown"] else "Risk score not yet computed."
            ),
            recommended_investigation=recs["investigation"],
            recommended_containment=recs["containment"],
            recommended_remediation=recs["remediation"],
            unknown_information=unknown,
            questions_for_analyst=[
                "Is this user/host expected to generate this kind of activity as part of their normal role?",
                "Has this source IP been seen in prior incidents?",
            ],
            generated_by=self.name,
            generated_at=datetime.now(timezone.utc),
        )
