import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def broadcast(self, conversation_id: int, data: dict):
        message = json.dumps(data, default=str)
        logger.info("WS broadcast type=%s conv=%s to %d connections", data.get("type"), conversation_id, len(self.connections))
        disconnected = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
                logger.info("WS sent to connection OK")
            except Exception as e:
                logger.warning("WS send failed: %s", e)
                disconnected.append(ws)
        for ws in disconnected:
            self.connections.remove(ws)


manager = WebSocketManager()
