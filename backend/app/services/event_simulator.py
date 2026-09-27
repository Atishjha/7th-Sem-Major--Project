"""
Event Simulator runtime.

Single in-memory runner (fine for this single-process academic demo).
Each event is: waited-for (to feel live) -> inserted into the DB and
committed -> broadcast over WebSocket. DB commit happens before the
broadcast so `GET /api/events` and the WebSocket never disagree.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from app.database.session import SessionLocal
from app.models.event import Event
from app.schemas.event import EventOut
from app.services.event_scenarios import SCENARIOS
from app.services.ws_manager import manager
from app.utils.ids import next_event_id
class SimulatorRunner:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.running: bool = False
        self.scenario: str | None = None
        self.events_emitted: int = 0
        self.total_events: int | None = None
        self.started_at: datetime | None = None
    def status(self) -> dict:
        return {
            "running": self.running,
            "scenario": self.scenario,
            "events_emitted": self.events_emitted,
            "total_events": self.total_events,
            "started_at": self.started_at,
        }
    async def start(self, scenario_key: str) -> None:
        if self.running:
            raise RuntimeError("A scenario is already running")
        if scenario_key not in SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario_key}'")

        self.running = True
        self.scenario = scenario_key
        self.events_emitted = 0
        self.started_at = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._run(scenario_key))
    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._reset()
        await manager.broadcast({"type": "status", "data": self.status()})
    def _reset(self) -> None:
        self.running = False
        self.scenario = None
        self.events_emitted = 0
        self.total_events = None
        self.started_at = None
    async def _run(self, scenario_key: str) -> None:
        generator = SCENARIOS[scenario_key]
        plan = generator()
        self.total_events = len(plan)
        await manager.broadcast({"type": "status", "data": self.status()})
        db = SessionLocal()
        try:
            clock = datetime.now(timezone.utc)
            for delay, fields in plan:
                await asyncio.sleep(delay)
                clock = clock + timedelta(seconds=delay)

                event = Event(timestamp=clock, **fields)
                event_id_num, event_id_str = next_event_id(db)
                event.id = event_id_num
                event.event_id = event_id_str
                db.add(event)
                db.commit()
                db.refresh(event)

                self.events_emitted += 1

                payload = EventOut.model_validate(event).model_dump(mode="json")
                await manager.broadcast({"type": "event", "data": payload})
                await manager.broadcast({"type": "status", "data": self.status()})
        except asyncio.CancelledError:
            db.rollback()
            raise
        finally:
            db.close()
            self._reset()
            await manager.broadcast({"type": "status", "data": self.status()})
simulator_runner = SimulatorRunner()
