"""
Default detection rule definitions.

These seed the `detection_rules` table on first startup. After that,
the table is the source of truth — editing a rule via
`POST /api/rules` changes its behavior immediately, with no code
change or redeploy needed. This is what the spec means by
"rules must be configurable."
"""

DEFAULT_RULES = [
    {
        "rule_key": "brute_force",
        "name": "Brute Force",
        "description": (
            "Flags repeated failed logins from the same source IP within "
            "a short window."
        ),
        "enabled": True,
        "config": {"failed_threshold": 5, "window_minutes": 5, "confidence": "high"},
    },
    {
        "rule_key": "suspicious_powershell",
        "name": "Suspicious PowerShell",
        "description": (
            "Flags process-execution events matching a known suspicious "
            "command-line pattern (e.g. hidden window, encoded command)."
        ),
        "enabled": True,
        "config": {"flagged_process": "powershell.exe", "confidence": "high"},
    },
    {
        "rule_key": "impossible_travel",
        "name": "Impossible Travel",
        "description": (
            "Flags a login location change for the same user shortly after "
            "their previous successful login (approximated via a location-"
            "change signal, not true geo-distance physics)."
        ),
        "enabled": True,
        "config": {"window_minutes": 10, "confidence": "medium"},
    },
    {
        "rule_key": "dns_anomaly",
        "name": "DNS Anomaly",
        "description": (
            "Flags an unusually high DNS query rate from the same source "
            "within a short window."
        ),
        "enabled": True,
        "config": {"query_threshold": 6, "window_seconds": 60, "confidence": "medium"},
    },
    {
        "rule_key": "abnormal_network",
        "name": "Abnormal Network Activity",
        "description": (
            "Flags network telemetry reporting an unusually high number of "
            "distinct destinations or outbound byte volume."
        ),
        "enabled": True,
        "config": {
            "unique_destination_threshold": 10,
            "bytes_sent_threshold": 50_000_000,
            "bytes_sent_critical_threshold": 200_000_000,
            "confidence": "medium",
        },
    },
]
