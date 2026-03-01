## 1. Dependencies & Configuration

- [x] 1.1 Add `itsdangerous` to pyproject.toml dependencies
- [x] 1.2 Add `app_password: str = ""` and `session_max_age: int = 604800` to Settings in `app/config.py`

## 2. Auth Module

- [x] 2.1 Create `app/auth.py` with: `create_session_cookie(password)` using `URLSafeTimedSerializer`, `validate_session_cookie(cookie)` returning bool, timing-safe password check
- [x] 2.2 Create in-memory rate limiter in `app/auth.py`: `check_rate_limit(ip)` returning bool, 5 attempts/min/IP, lazy cleanup of old entries
- [x] 2.3 Write tests for auth module (cookie creation, validation, expiry, tampering, rate limit enforcement and reset)

## 3. Login & Logout Endpoints

- [x] 3.1 Create `app/routes/login.py` with `POST /login` (validate password, set cookie, rate limit) and `POST /logout` (clear cookie)
- [x] 3.2 Write tests for login/logout endpoints (correct password, wrong password, rate limit exceeded, logout clears cookie)

## 4. Auth Middleware

- [x] 4.1 Create `AuthMiddleware` in `app/auth.py` (or `app/middleware.py`): check cookie on every request, allowlist for `/webhook`, `/login`, `/login.html`, static login assets. Return 401 for API, redirect for HTML. Skip entirely when `APP_PASSWORD` is empty.
- [x] 4.2 Register middleware in `app/main.py`
- [x] 4.3 Write tests for middleware (protected routes return 401, allowlisted routes pass through, middleware disabled when no password set)

## 5. WebSocket Auth

- [x] 5.1 Add cookie validation to WebSocket endpoint in `app/main.py`: reject with close code 4401 if invalid
- [x] 5.2 Write test for WebSocket auth (reject without cookie, accept with valid cookie)

## 6. Frontend - Login Page

- [x] 6.1 Create `app/static/login.html` with password input, submit button, error message display
- [x] 6.2 Add 401 handler in `app.js`: intercept fetch responses, redirect to `/login.html` on 401
