from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User, UserRole
from app.schemas.event import SimulatorStartRequest, SimulatorStatus
from app.security.dependencies import get_current_user, require_role
from app.services.event_simulator import simulator_runner
from app.services.audit import log_action
from app.database.session import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/simulator", tags=["simulator"])

can_control_simulator = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)


@router.post("/start", response_model=SimulatorStatus)
async def start_simulator(
    payload: SimulatorStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(can_control_simulator),
) -> dict:
    try:
        await simulator_runner.start(payload.scenario.value)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    log_action(
        db, username=user.username, action=f"Started demo scenario '{payload.scenario.value}'",
        resource_type="simulator", resource_id=payload.scenario.value,
        new_value={"scenario": payload.scenario.value},
    )
    return simulator_runner.status()


@router.post("/stop", response_model=SimulatorStatus)
async def stop_simulator(db: Session = Depends(get_db), user: User = Depends(can_control_simulator)) -> dict:
    was_running = simulator_runner.scenario
    await simulator_runner.stop()
    log_action(
        db, username=user.username, action="Stopped demo scenario",
        resource_type="simulator", resource_id=was_running,
        old_value={"scenario": was_running} if was_running else None,
    )
    return simulator_runner.status()


@router.get("/status", response_model=SimulatorStatus)
def simulator_status(_: User = Depends(get_current_user)) -> dict:
    return simulator_runner.status()
