from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.auth import check_password, create_session_cookie, check_rate_limit, get_operator_from_request, COOKIE_NAME
from app.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    password: str
    operator: str | None = None


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(client_ip):
        response.status_code = 429
        return {"detail": "Too many attempts. Try again later."}

    if not check_password(req.password):
        response.status_code = 401
        return {"detail": "Wrong password."}

    operator_list = settings.operator_list
    if operator_list:
        if not req.operator or req.operator not in operator_list:
            response.status_code = 400
            return {"detail": "Selecione um operador."}

    cookie = create_session_cookie(operator=req.operator if operator_list else None)
    response.set_cookie(
        key=COOKIE_NAME,
        value=cookie,
        max_age=settings.session_max_age,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
    )
    return {"status": "ok"}


@router.get("/api/operators")
async def get_operators():
    return {"operators": settings.operator_list}


@router.get("/api/me")
async def get_me(request: Request):
    operator = get_operator_from_request(request)
    return {"operator": operator}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"status": "ok"}
