"""
Synthetic scenario generators for the Event Simulator / Demo Mode.

Every scenario returns an ordered list of (delay_seconds, fields)
tuples: `delay_seconds` is how long to wait after the previous event
before emitting this one, and `fields` is everything needed to build
an `Event` row except `event_id`/`timestamp` (added by the runner).

All indicators are deliberately synthetic and non-resolvable:
- IPs come from IANA documentation ranges (RFC 5737: 192.0.2.0/24,
  198.51.100.0/24, 203.0.113.0/24) or private ranges (RFC 1918).
- Domains use the .invalid TLD (RFC 2606), which can never resolve.
- "Suspicious command" text is a labeled placeholder, never a real
  working command line.

This module only *describes* telemetry that a defensive analyst would
investigate. It performs no scanning, no execution, and no network
activity of any kind — everything here is just Python data.
"""

import random
import uuid

from app.models.common import Severity

USERS = ["demo_user", "demo_admin", "j.doe.demo", "a.patel.demo"]
HOSTS = ["WIN-CLIENT-01", "WIN-CLIENT-02", "WIN-SRV-DB01", "WIN-SRV-WEB01"]
INTERNAL_IPS = ["192.168.56.10", "192.168.56.11", "192.168.56.20", "10.10.0.15"]
SUSPICIOUS_EXTERNAL_IPS = ["203.0.113.25", "203.0.113.77", "203.0.113.140"]
DOC_DEST_IPS = ["198.51.100.23", "198.51.100.77", "198.51.100.201"]
SYNTHETIC_LOCATIONS = [
    "Lagos, NG (synthetic)",
    "Bucharest, RO (synthetic)",
    "Manila, PH (synthetic)",
]
HOME_LOCATION = "Bhubaneswar, IN (synthetic)"


def _evt(
    source: str,
    event_type: str,
    action: str,
    status: str,
    severity: Severity,
    message: str,
    *,
    source_ip: str | None = None,
    destination_ip: str | None = None,
    username: str | None = None,
    hostname: str | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "source": source,
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "username": username,
        "hostname": hostname,
        "event_type": event_type,
        "action": action,
        "status": status,
        "severity": severity,
        "message": message,
        "event_metadata": metadata or {},
    }


def scenario_brute_force() -> list[tuple[float, dict]]:
    user = random.choice(USERS)
    host = random.choice(HOSTS)
    attacker_ip = random.choice(SUSPICIOUS_EXTERNAL_IPS)
    events: list[tuple[float, dict]] = []

    fail_count = random.randint(5, 8)
    for i in range(fail_count):
        events.append((
            1.0,
            _evt(
                "authentication", "login", "login", "failed", Severity.MEDIUM,
                "Failed authentication attempt",
                source_ip=attacker_ip, username=user, hostname=host,
                metadata={"attempt": i + 1},
            ),
        ))

    events.append((
        1.5,
        _evt(
            "authentication", "login", "login", "success", Severity.MEDIUM,
            "Authentication succeeded after repeated failures",
            source_ip=attacker_ip, username=user, hostname=host,
            metadata={"preceding_failures": fail_count},
        ),
    ))
    events.append((
        1.0,
        _evt(
            "authentication", "new_location", "login", "n/a", Severity.HIGH,
            "Login observed from unusual location",
            source_ip=attacker_ip, username=user, hostname=host,
            metadata={
                "observed_location": random.choice(SYNTHETIC_LOCATIONS),
                "usual_location": HOME_LOCATION,
            },
        ),
    ))
    events.append((
        1.0,
        _evt(
            "authentication", "suspicious_activity", "session_activity", "n/a",
            Severity.HIGH, "Suspicious post-login activity detected",
            source_ip=attacker_ip, username=user, hostname=host,
        ),
    ))
    return events


def scenario_powershell() -> list[tuple[float, dict]]:
    host = random.choice(HOSTS)
    user = random.choice(USERS)
    internal_ip = random.choice(INTERNAL_IPS)
    events: list[tuple[float, dict]] = []

    events.append((
        0.5,
        _evt(
            "endpoint", "process_execution", "start", "n/a", Severity.LOW,
            "Process started: explorer.exe",
            source_ip=internal_ip, username=user, hostname=host,
            metadata={"process": "explorer.exe"},
        ),
    ))
    events.append((
        1.5,
        _evt(
            "endpoint", "process_execution", "start", "n/a", Severity.MEDIUM,
            "powershell.exe executed",
            source_ip=internal_ip, username=user, hostname=host,
            metadata={"process": "powershell.exe", "parent_process": "explorer.exe"},
        ),
    ))
    events.append((
        1.5,
        _evt(
            "endpoint", "process_execution", "command", "n/a", Severity.HIGH,
            "Suspicious PowerShell command pattern detected",
            source_ip=internal_ip, username=user, hostname=host,
            metadata={
                "process": "powershell.exe",
                "command_line": "powershell.exe -NoProfile -WindowStyle Hidden -Command <SYNTHETIC_PLACEHOLDER>",
                "pattern_matched": "hidden_window_flag",
            },
        ),
    ))
    events.append((
        1.0,
        _evt(
            "endpoint", "endpoint_behavior", "flag", "n/a", Severity.CRITICAL,
            "Endpoint flagged for suspicious script execution",
            source_ip=internal_ip, username=user, hostname=host,
        ),
    ))
    return events


def scenario_dns_anomaly() -> list[tuple[float, dict]]:
    host = random.choice(HOSTS)
    internal_ip = random.choice(INTERNAL_IPS)
    events: list[tuple[float, dict]] = []

    query_count = random.randint(6, 10)
    for i in range(query_count):
        subdomain = uuid.uuid4().hex[:10]
        events.append((
            0.3,
            _evt(
                "dns", "dns_query", "query", "n/a", Severity.LOW,
                "DNS query observed",
                source_ip=internal_ip, hostname=host,
                metadata={"domain": f"{subdomain}.example-test.invalid"},
            ),
        ))

    events.append((
        1.0,
        _evt(
            "dns", "dns_anomaly", "volume_spike", "n/a", Severity.HIGH,
            "Unusually high DNS query volume detected",
            source_ip=internal_ip, hostname=host,
            metadata={"query_count": query_count, "window_seconds": 30},
        ),
    ))
    events.append((
        1.0,
        _evt(
            "dns", "dns_anomaly", "pattern_match", "n/a", Severity.HIGH,
            "DNS queries matching unusual randomized domain pattern",
            source_ip=internal_ip, hostname=host,
            metadata={"pattern": "high_entropy_subdomain"},
        ),
    ))
    return events


def scenario_network_anomaly() -> list[tuple[float, dict]]:
    host = random.choice(HOSTS)
    internal_ip = random.choice(INTERNAL_IPS)
    events: list[tuple[float, dict]] = []

    for _ in range(2):
        events.append((
            0.8,
            _evt(
                "network", "network_connection", "connect", "n/a", Severity.LOW,
                "Normal outbound connection",
                source_ip=internal_ip,
                destination_ip=random.choice(DOC_DEST_IPS),
                hostname=host,
            ),
        ))

    dest_count = random.randint(12, 25)
    events.append((
        1.0,
        _evt(
            "network", "network_anomaly", "connection_spike", "n/a",
            Severity.MEDIUM, "Sudden increase in outbound connections",
            source_ip=internal_ip, hostname=host,
            metadata={"connections_per_minute": dest_count * 3},
        ),
    ))
    events.append((
        1.0,
        _evt(
            "network", "network_anomaly", "multi_destination", "n/a",
            Severity.MEDIUM, "Connections to multiple distinct destinations observed",
            source_ip=internal_ip, hostname=host,
            metadata={"unique_destinations": dest_count},
        ),
    ))
    events.append((
        1.0,
        _evt(
            "network", "network_anomaly", "abnormal_outbound", "n/a",
            Severity.HIGH, "Abnormal outbound traffic volume detected",
            source_ip=internal_ip,
            destination_ip=random.choice(SUSPICIOUS_EXTERNAL_IPS),
            hostname=host,
            metadata={"bytes_sent": random.randint(50_000_000, 500_000_000)},
        ),
    ))
    return events


def scenario_multi_stage() -> list[tuple[float, dict]]:
    """The flagship demo: brute force -> PowerShell -> network anomaly,
    all tied to the same user/host so later phases can correlate them
    into a single incident."""
    # Fresh synthetic entities every run (RFC 5737 IP, .demo user, made-up
    # host) so the flagship demo always opens its own clean incident
    # instead of merging into one left over from earlier scenarios that
    # drew from the small shared pools above. Rehearsing it twice gives
    # two separate incidents.
    user = f"{random.choice(['m.rossi', 'k.tanaka', 's.okafor', 'l.novak', 't.silva'])}{random.randint(10, 99)}.demo"
    host = f"WIN-CLIENT-{random.randint(10, 99)}"
    attacker_ip = f"203.0.113.{random.randint(100, 250)}"
    events: list[tuple[float, dict]] = []

    fail_count = 5  # matches the brute_force rule's default threshold
    for i in range(fail_count):
        events.append((
            0.8,
            _evt(
                "authentication", "login", "login", "failed", Severity.MEDIUM,
                "Failed authentication attempt",
                source_ip=attacker_ip, username=user, hostname=host,
                metadata={"attempt": i + 1},
            ),
        ))
    events.append((
        1.2,
        _evt(
            "authentication", "login", "login", "success", Severity.MEDIUM,
            "Authentication succeeded after repeated failures",
            source_ip=attacker_ip, username=user, hostname=host,
        ),
    ))
    events.append((
        1.0,
        _evt(
            "authentication", "new_location", "login", "n/a", Severity.HIGH,
            "Login observed from unusual location",
            source_ip=attacker_ip, username=user, hostname=host,
            metadata={
                "observed_location": random.choice(SYNTHETIC_LOCATIONS),
                "usual_location": HOME_LOCATION,
            },
        ),
    ))
    events.append((
        1.2,
        _evt(
            "endpoint", "process_execution", "start", "n/a", Severity.MEDIUM,
            "powershell.exe executed",
            source_ip=attacker_ip, username=user, hostname=host,
            metadata={"process": "powershell.exe"},
        ),
    ))
    events.append((
        1.2,
        _evt(
            "endpoint", "process_execution", "command", "n/a", Severity.HIGH,
            "Suspicious PowerShell command pattern detected",
            source_ip=attacker_ip, username=user, hostname=host,
            metadata={
                "process": "powershell.exe",
                "command_line": "powershell.exe -NoProfile -WindowStyle Hidden -Command <SYNTHETIC_PLACEHOLDER>",
                "pattern_matched": "hidden_window_flag",
            },
        ),
    ))
    events.append((
        1.0,
        _evt(
            "network", "network_anomaly", "abnormal_outbound", "n/a",
            Severity.CRITICAL, "Abnormal outbound traffic volume detected",
            source_ip=attacker_ip, hostname=host,
            destination_ip=random.choice(SUSPICIOUS_EXTERNAL_IPS),
            metadata={"bytes_sent": random.randint(50_000_000, 500_000_000)},
        ),
    ))
    return events


SCENARIOS = {
    "brute_force": scenario_brute_force,
    "powershell": scenario_powershell,
    "dns_anomaly": scenario_dns_anomaly,
    "network_anomaly": scenario_network_anomaly,
    "multi_stage": scenario_multi_stage,
}
