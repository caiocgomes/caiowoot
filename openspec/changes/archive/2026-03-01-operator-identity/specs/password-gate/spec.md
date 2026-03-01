## MODIFIED Requirements

### Requirement: Maintain session via signed cookie
The system SHALL issue a signed cookie (using `itsdangerous` `URLSafeTimedSerializer`) upon successful login. The cookie SHALL have: `HttpOnly` flag set, `SameSite=Strict`, `Secure` flag when not in development, configurable max age via `SESSION_MAX_AGE` env var (default 7 days). The cookie payload SHALL include the operator name when operators are configured: `{"authenticated": True, "operator": "<name>"}`.

#### Scenario: Valid session cookie on request
- **WHEN** a request includes a valid, non-expired session cookie
- **THEN** the system SHALL allow the request to proceed

#### Scenario: Expired session cookie
- **WHEN** a request includes an expired session cookie
- **THEN** the system SHALL redirect to the login page (HTML requests) or return 401 (API requests)

#### Scenario: Tampered session cookie
- **WHEN** a request includes a cookie with an invalid signature
- **THEN** the system SHALL reject the request and clear the cookie

#### Scenario: Valid cookie without operator field when operators are configured
- **WHEN** a request includes a valid session cookie without the `operator` field AND `OPERATORS` is configured
- **THEN** the system SHALL treat the session as invalid and redirect to the login page
