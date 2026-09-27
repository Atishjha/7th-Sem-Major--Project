"""
In-memory WebSocket connection manager.

Single-process demo scope: fine for the academic project as described
(no multi-worker/multi-node fan-out is required). Dead connections are
dropped silently on broadcast failure.
"""
import json
from typing import Any
from fastapi import WebSocket
class ConnectionManager:
    def __init__(self) -> None:
        self._connections : list[WebSocket] = []
    async def connect(self,websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
    def disconnect(self,websocket:WebSocket)->None:
        if websocket in self._connections:
            self._connections.remove(websocket)
    async def broadcast(self,payload: dict[str,Any]) -> None:
        message = json.dumps(payload,default=str)
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)
            
manager = ConnectionManager()