from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User, UserRole
from app.schemas.event import SimulatorStartRequest, SimulatorStatus
from app.security.dependencies import get_current_user, require_role
from app.services.event_simulator import simulator_runner
router = APIRouter(prefix="/simulator", tags=["simulator"])
can_control_simulator = require_role(UserRole.ADMIN, UserRole.SOC_ANALYST)
@router.post("/start", response_model=SimulatorStatus)
async def start_simulator(
    payload: SimulatorStartRequest,
    _: User = Depends(can_control_simulator),
) -> dict:
    try:
        await simulator_runner.start(payload.scenario.value)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return simulator_runner.status()
@router.post("/stop", response_model=SimulatorStatus)
async def stop_simulator(_: User = Depends(can_control_simulator)) -> dict:
    await simulator_runner.stop()
    return simulator_runner.status()
@router.get("/status", response_model=SimulatorStatus)
def simulator_status(_: User = Depends(get_current_user)) -> dict:
    return simulator_runner.status()
