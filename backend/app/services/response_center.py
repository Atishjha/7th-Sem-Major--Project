"""
Response Center: AI Recommendation -> Analyst Review -> Approve/Reject
-> Mock Action -> Result. Every action is simulated — nothing here
ever touches a real account, endpoint, session, credential, or
firewall. Every result message says so explicitly, matching the
spec's own example format exactly.

Recommendations are deterministic and data-driven by incident_type
(reusing the same incident_type values Phase 7's correlator already
assigns), targeting the incident's own real primary entity — never a
placeholder. `create_recommended_actions` is idempotent: re-opening
the Response tab never duplicates an already-recommended action.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.incident import Incident
from app.models.response_action import ActionStatus, ActionType, ResponseAction
from app.models.user import User
from app.utils.ids import next_response_id
from app.schemas.response import ResponseActionOut
ACTION_LABELS = {
    ActionType.DISABLE_ACCOUNT: "Disable Account",
    ActionType.REVOKE_SESSION: "Revoke Session",
    ActionType.ISOLATE_ENDPOINT: "Isolate Endpoint",
    ActionType.BLOCK_INDICATOR: "Block Indicator",
    ActionType.RESET_CREDENTIALS: "Reset Credentials",
    ActionType.CREATE_FIREWALL_RULE: "Create Firewall Rule",
}

_RESULT_TEMPLATES = {
    ActionType.DISABLE_ACCOUNT: lambda t: f"Demo account '{t}' would be disabled. No real account was modified.",
    ActionType.REVOKE_SESSION: lambda t: f"Demo session(s) for '{t}' would be revoked. No real session was modified.",
    ActionType.ISOLATE_ENDPOINT: lambda t: f"Demo endpoint {t} would be isolated. No real endpoint was modified.",
    ActionType.BLOCK_INDICATOR: lambda t: f"Demo indicator {t} would be blocked at the perimeter. No real firewall or block list was modified.",
    ActionType.RESET_CREDENTIALS: lambda t: f"Demo credentials for '{t}' would be reset. No real credentials were modified.",
    ActionType.CREATE_FIREWALL_RULE: lambda t: f"Demo firewall rule blocking {t} would be created. No real firewall was modified.",
}

# incident_type -> [(action_type, which incident field to target, reason)]
RECOMMENDATION_RULES: dict[str, list[tuple[ActionType, str, str]]] = {
    "account_compromise": [
        (ActionType.DISABLE_ACCOUNT, "primary_username",
         "Account shows signs of compromise (brute force and/or impossible travel)."),
        (ActionType.RESET_CREDENTIALS, "primary_username",
         "Credentials may be compromised; reset recommended before re-enabling access."),
        (ActionType.REVOKE_SESSION, "primary_username",
         "Any active sessions for this account should be terminated pending review."),
    ],
    "endpoint_compromise": [
        (ActionType.ISOLATE_ENDPOINT, "primary_hostname",
         "Suspicious PowerShell execution detected; isolate to prevent lateral movement."),
    ],
    "suspicious_network": [
        (ActionType.BLOCK_INDICATOR, "primary_source_ip",
         "Source associated with both anomalous DNS and abnormal network activity."),
        (ActionType.CREATE_FIREWALL_RULE, "primary_source_ip",
         "Proactively block this source at the perimeter pending investigation."),
    ],
    "dns_anomaly": [
        (ActionType.BLOCK_INDICATOR, "primary_source_ip",
         "Source generated DNS query volume exceeding the configured threshold."),
    ],
    "network_anomaly": [
        (ActionType.BLOCK_INDICATOR, "primary_source_ip",
         "Source generated abnormal outbound network activity."),
    ],
}


def _result_message(action_type: ActionType, target: str) -> str:
    return _RESULT_TEMPLATES[action_type](target)


def create_recommended_actions(db: Session, incident: Incident) -> list[ResponseAction]:
    rules = RECOMMENDATION_RULES.get(incident.incident_type, [])
    existing = {
        (a.action_type, a.target)
        for a in db.scalars(select(ResponseAction).where(ResponseAction.incident_id == incident.id))
    }

    created: list[ResponseAction] = []
    for action_type, target_field, reason in rules:
        target = getattr(incident, target_field, None)
        if not target or (action_type, target) in existing:
            continue
        response_id_num, response_id_str = next_response_id(db)
        action = ResponseAction(
            id=response_id_num,
            response_id=response_id_str,
            incident_id=incident.id,
            action_type=action_type,
            target=target,
            recommended_reason=reason,
            status=ActionStatus.RECOMMENDED,
        )
        db.add(action)
        created.append(action)

    if created:
        db.commit()
        for a in created:
            db.refresh(a)
    return created


def approve_action(db: Session, action: ResponseAction, user: User) -> ResponseAction:
    action.status = ActionStatus.SIMULATED_SUCCESS
    action.result_message = _result_message(action.action_type, action.target)
    action.decided_by_username = user.username
    action.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action


def reject_action(db: Session, action: ResponseAction, user: User) -> ResponseAction:
    action.status = ActionStatus.REJECTED
    action.result_message = "Rejected by analyst; no action taken."
    action.decided_by_username = user.username
    action.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action


def serialize_action(action: ResponseAction) -> ResponseActionOut:
    return ResponseActionOut(
        id=action.id,
        response_id=action.response_id,
        incident_id=action.incident_id,
        action_type=action.action_type,
        action_label=ACTION_LABELS[action.action_type],
        target=action.target,
        recommended_reason=action.recommended_reason,
        status=action.status,
        result_message=action.result_message,
        decided_by_username=action.decided_by_username,
        decided_at=action.decided_at,
        created_at=action.created_at,
    )
