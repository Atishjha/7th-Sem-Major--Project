"""
Live event/status stream.

Deliberately unauthenticated for this academic demo: it only ever
broadcasts synthetic telemetry that is also readable via the
authenticated `GET /api/events`, so there's nothing sensitive to
protect here. A production system would authenticate the WebSocket
handshake (e.g. a short-lived token in the query string); noted in
the README as a known, intentional simplification.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager
router = APIRouter(tags=["websocket"])
@router.websocket("/ws/events")
async def events_ws(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect inbound messages, but need to keep the
            # coroutine alive to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
