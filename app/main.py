import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import init_db
from app.routes import conversations, messages, webhook
from app.websocket_manager import manager

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CaioWoot", lifespan=lifespan)


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.endswith((".js", ".css", ".html")) or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app.add_middleware(NoCacheStaticMiddleware)

app.include_router(webhook.router)
app.include_router(conversations.router)
app.include_router(messages.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
