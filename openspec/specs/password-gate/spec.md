## ADDED Requirements

### Requirement: Authenticate with shared password
The system SHALL require a shared password (configured via environment variable `APP_PASSWORD`) to access any protected route. The password SHALL be compared using timing-safe comparison (`hmac.compare_digest`) to prevent timing attacks.

#### Scenario: Correct password submitted
- **WHEN** a user submits the correct password via POST /login
- **THEN** the system SHALL set a signed session cookie and return 200 OK

#### Scenario: Incorrect password submitted
- **WHEN** a user submits an incorrect password via POST /login
- **THEN** the system SHALL return 401 Unauthorized without setting a cookie

#### Scenario: APP_PASSWORD not configured
- **WHEN** the application starts without `APP_PASSWORD` set
- **THEN** the authentication middleware SHALL be disabled and all routes SHALL be accessible without login

### Requirement: Maintain session via signed cookie
The system SHALL issue a signed cookie (using `itsdangerous` `URLSafeTimedSerializer`) upon successful login. The cookie SHALL have: `HttpOnly` flag set, `SameSite=Strict`, `Secure` flag when not in development, configurable max age via `SESSION_MAX_AGE` env var (default 7 days).

#### Scenario: Valid session cookie on request
- **WHEN** a request includes a valid, non-expired session cookie
- **THEN** the system SHALL allow the request to proceed

#### Scenario: Expired session cookie
- **WHEN** a request includes an expired session cookie
- **THEN** the system SHALL redirect to the login page (HTML requests) or return 401 (API requests)

#### Scenario: Tampered session cookie
- **WHEN** a request includes a cookie with an invalid signature
- **THEN** the system SHALL reject the request and clear the cookie

### Requirement: Protect all routes except allowlist
The system SHALL intercept all HTTP requests with an authentication middleware. The following routes SHALL be exempt (allowlist): `POST /webhook`, `POST /login`, `GET /login.html`, static assets needed for the login page. All other routes SHALL require a valid session.

#### Scenario: Unauthenticated request to protected route
- **WHEN** an unauthenticated user requests a protected API route
- **THEN** the system SHALL return 401 Unauthorized

#### Scenario: Unauthenticated request to frontend
- **WHEN** an unauthenticated user requests the main page (/)
- **THEN** the system SHALL redirect to the login page

#### Scenario: Request to webhook endpoint
- **WHEN** Evolution API posts to /webhook without a session cookie
- **THEN** the system SHALL allow the request (webhook is in the allowlist)

### Requirement: Rate limit login attempts
The system SHALL enforce rate limiting on the POST /login endpoint: maximum 5 attempts per IP address per minute. Rate state SHALL be stored in-memory (no external dependency).

#### Scenario: Rate limit exceeded
- **WHEN** an IP address exceeds 5 login attempts within 1 minute
- **THEN** the system SHALL return 429 Too Many Requests

#### Scenario: Rate limit resets after window
- **WHEN** 1 minute has passed since the first attempt in a window
- **THEN** the IP address SHALL be allowed to attempt login again

### Requirement: Protect WebSocket connections
The system SHALL validate the session cookie during the WebSocket handshake, before accepting the connection.

#### Scenario: WebSocket with valid session
- **WHEN** a WebSocket connection request includes a valid session cookie
- **THEN** the system SHALL accept the connection

#### Scenario: WebSocket without valid session
- **WHEN** a WebSocket connection request has no session cookie or an invalid one
- **THEN** the system SHALL reject the connection with close code 4401

### Requirement: Logout
The system SHALL provide a POST /logout endpoint that clears the session cookie and redirects to the login page.

#### Scenario: Successful logout
- **WHEN** an authenticated user sends POST /logout
- **THEN** the system SHALL clear the session cookie and return 200 OK
