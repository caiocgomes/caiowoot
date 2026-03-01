from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.auth import check_password, create_session_cookie, check_rate_limit, COOKIE_NAME
from app.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(client_ip):
        response.status_code = 429
        return {"detail": "Too many attempts. Try again later."}

    if not check_password(req.password):
        response.status_code = 401
        return {"detail": "Wrong password."}

    cookie = create_session_cookie()
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie,
        max_age=settings.session_max_age,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
    )
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "ok"}
