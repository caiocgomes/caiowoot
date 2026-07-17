## ADDED Requirements

### Requirement: Playwright and pytest-playwright as dev dependencies
The project SHALL include `playwright` and `pytest-playwright` as dev dependencies in `pyproject.toml`. Chromium browser SHALL be installed via `playwright install chromium`.

#### Scenario: Dependencies installed
- **WHEN** `uv sync` is run
- **THEN** playwright and pytest-playwright SHALL be available in the environment

#### Scenario: Chromium available
- **WHEN** `playwright install chromium` has been run
- **THEN** Playwright SHALL be able to launch a headless Chromium browser

### Requirement: Live server fixture for e2e tests
The e2e test suite SHALL provide a pytest fixture (`live_server`) that starts the FastAPI app on a random available port using uvicorn in a background thread. The fixture SHALL yield the base URL and shut down the server after tests complete.

#### Scenario: Server starts before tests
- **WHEN** a test function requests the `live_server` fixture
- **THEN** the FastAPI app SHALL be running and accepting HTTP requests at the yielded URL

#### Scenario: Server stops after tests
- **WHEN** all tests in the session complete
- **THEN** the uvicorn server SHALL be shut down cleanly

#### Scenario: Port isolation
- **WHEN** multiple test sessions run in parallel
- **THEN** each session SHALL use a different random port to avoid conflicts

### Requirement: Page fixture with base URL
The e2e test suite SHALL provide a `page` fixture (via pytest-playwright) configured with the `live_server` base URL. The page SHALL use Chromium in headless mode.

#### Scenario: Page navigates to app
- **WHEN** a test calls `page.goto("/")`
- **THEN** the page SHALL load the CaioWoot index.html from the live server

### Requirement: Mobile and desktop viewport fixtures
The e2e test suite SHALL provide viewport preset fixtures: `mobile_page` (390x844, iPhone 14 equivalent) and `desktop_page` (1280x800). Tests SHALL use these to validate responsive behavior.

#### Scenario: Mobile viewport
- **WHEN** a test uses the `mobile_page` fixture
- **THEN** the browser viewport SHALL be 390x844 pixels

#### Scenario: Desktop viewport
- **WHEN** a test uses the `desktop_page` fixture
- **THEN** the browser viewport SHALL be 1280x800 pixels

### Requirement: Test database seeded with conversation data
The e2e test suite SHALL seed the database with at least one conversation containing: inbound messages, outbound human messages, outbound bot messages, and pending drafts. This provides a realistic state for visual validation.

#### Scenario: Seeded conversation available
- **WHEN** the live server starts with the test database
- **THEN** at least one conversation SHALL appear in the sidebar with messages of all types

#### Scenario: Drafts available for testing
- **WHEN** the seeded conversation is opened
- **THEN** pending draft cards SHALL be visible for carousel and selection testing

### Requirement: E2e tests in tests/e2e/ directory
All Playwright-based e2e tests SHALL be placed in `tests/e2e/` directory. They SHALL be runnable via `uv run pytest tests/e2e/ -v` and SHALL NOT interfere with existing backend tests in `tests/`.

#### Scenario: E2e tests run independently
- **WHEN** `uv run pytest tests/e2e/ -v` is executed
- **THEN** only e2e tests SHALL run, not backend unit/integration tests

#### Scenario: Backend tests unaffected
- **WHEN** `uv run pytest tests/ -v --ignore=tests/e2e` is executed
- **THEN** all existing backend tests SHALL pass without changes
