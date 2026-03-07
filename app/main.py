import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.auth import AuthMiddleware, validate_session_cookie, COOKIE_NAME
from app.database import init_db
from app.routes import admin, attachments, conversations, knowledge, login, messages, review, rules, settings, webhook
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
app.add_middleware(AuthMiddleware)

app.include_router(login.router)
app.include_router(webhook.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(knowledge.router)
app.include_router(rules.router)
app.include_router(review.router)
app.include_router(settings.router)
app.include_router(attachments.router)
app.include_router(admin.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    cookie = websocket.cookies.get(COOKIE_NAME, "")
    if not validate_session_cookie(cookie):
        await websocket.close(code=4401)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
