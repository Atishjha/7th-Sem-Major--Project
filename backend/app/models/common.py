"""
Shared enums used across multiple models (events now; alerts and
incidents reuse the same Severity in later phases so a "high"
event and a "high" alert always mean the same thing).
"""

import enum


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
