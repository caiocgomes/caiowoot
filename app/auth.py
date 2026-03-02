import hmac
import time

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.config import settings

COOKIE_NAME = "caiowoot_session"

# --- Session cookies ---

def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.app_password)


def check_password(password: str) -> bool:
    if not settings.app_password:
        return False
    return hmac.compare_digest(password, settings.app_password)


def create_session_cookie(operator: str | None = None) -> str:
    s = _get_serializer()
    payload = {"authenticated": True}
    if operator:
        payload["operator"] = operator
    return s.dumps(payload)


def _load_session(cookie: str) -> dict | None:
    if not cookie:
        return None
    s = _get_serializer()
    try:
        return s.loads(cookie, max_age=settings.session_max_age)
    except (BadSignature, SignatureExpired):
        return None


def validate_session_cookie(cookie: str) -> bool:
    if not settings.app_password:
        return True  # no password = no auth required
    session = _load_session(cookie)
    if not session:
        return False
    if settings.operator_list and not session.get("operator"):
        return False
    return True


def get_operator_from_request(request) -> str | None:
    cookie = request.cookies.get(COOKIE_NAME, "")
    session = _load_session(cookie)
    if not session:
        return None
    return session.get("operator")


def is_admin(operator_name: str | None) -> bool:
    if not settings.operator_list:
        return True
    admin = settings.admin_operator
    if not admin:
        admin = settings.operator_list[0] if settings.operator_list else ""
    return operator_name == admin


# --- Rate limiting ---

_rate_limit_store: dict[str, list[float]] = {}

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW

    if ip in _rate_limit_store:
        # Lazy cleanup: remove old entries
        _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > cutoff]
    else:
        _rate_limit_store[ip] = []

    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False

    _rate_limit_store[ip].append(now)
    return True


def reset_rate_limit():
    """For testing only."""
    _rate_limit_store.clear()


# --- Auth middleware ---

ALLOWLIST_PATHS = {"/webhook", "/login", "/logout", "/api/operators"}
ALLOWLIST_PREFIXES = ("/login.html", "/manifest.json", "/sw.js", "/icon-")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth entirely when no password is configured
        if not settings.app_password:
            return await call_next(request)

        path = request.url.path

        # Allow listed paths
        if path in ALLOWLIST_PATHS:
            return await call_next(request)

        # Allow login page and its static assets
        if any(path.startswith(p) for p in ALLOWLIST_PREFIXES):
            return await call_next(request)

        # Validate session cookie
        cookie = request.cookies.get(COOKIE_NAME, "")
        if validate_session_cookie(cookie):
            return await call_next(request)

        # Not authenticated
        accept = request.headers.get("accept", "")
        if "text/html" in accept and not path.startswith("/api"):
            return RedirectResponse("/login.html", status_code=302)

        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
