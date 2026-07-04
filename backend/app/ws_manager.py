import asyncio
import json

from fastapi import WebSocket


class WSManager:
    """Tracks browser sockets subscribed to a given run_id and fans out
    JSON messages to all of them."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, run_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(run_id, []).append(ws)

    async def disconnect(self, run_id: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(run_id, [])
            if ws in conns:
                conns.remove(ws)
            if not conns and run_id in self._connections:
                del self._connections[run_id]

    async def broadcast(self, run_id: str, message: dict) -> None:
        conns = self._connections.get(run_id, [])
        if not conns:
            return
        payload = json.dumps(message)
        stale = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(run_id, ws)


ws_manager = WSManager()
