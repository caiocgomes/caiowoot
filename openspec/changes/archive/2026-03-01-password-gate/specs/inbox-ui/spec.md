## ADDED Requirements

### Requirement: Display login page when unauthenticated
The system SHALL display a login page with a password input field and submit button when the user is not authenticated. The login page SHALL be a separate HTML page (`login.html`) that does not require authentication to load.

#### Scenario: Unauthenticated user visits the app
- **WHEN** a user navigates to the app without a valid session
- **THEN** the system SHALL redirect to the login page

#### Scenario: Successful login redirects to app
- **WHEN** the user submits the correct password on the login page
- **THEN** the system SHALL redirect to the main app (/)

#### Scenario: Wrong password shows error
- **WHEN** the user submits an incorrect password
- **THEN** the login page SHALL display an error message without reloading

### Requirement: Handle 401 responses in API calls
The system SHALL handle 401 responses from API calls by redirecting the user to the login page. This covers session expiration mid-use.

#### Scenario: Session expires during use
- **WHEN** the user's session expires while using the app
- **THEN** the next API call SHALL receive a 401 response
- **THEN** the frontend SHALL redirect to the login page
