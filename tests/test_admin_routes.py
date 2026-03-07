import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.conftest import *  # noqa: F401, F403


@pytest_asyncio.fixture
async def admin_db(db):
    """DB fixture with analysis tables created."""
    await db.execute("""CREATE TABLE IF NOT EXISTS analysis_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
        status TEXT DEFAULT 'running', total_conversations INTEGER DEFAULT 0,
        total_operators INTEGER DEFAULT 0, error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP)""")
    await db.execute("""CREATE TABLE IF NOT EXISTS conversation_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_run_id INTEGER NOT NULL,
        conversation_id INTEGER NOT NULL, operator_name TEXT, engagement_level TEXT,
        sale_status TEXT, recovery_potential TEXT, recovery_suggestion TEXT,
        factual_issues_json TEXT, overall_assessment TEXT, metrics_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    await db.execute("""CREATE TABLE IF NOT EXISTS operator_digests (
        id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_run_id INTEGER NOT NULL,
        operator_name TEXT NOT NULL, summary TEXT, patterns_json TEXT,
        factual_issues_json TEXT, salvageable_sales_json TEXT, metrics_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    await db.commit()
    yield db


@pytest.mark.asyncio
async def test_admin_analysis_forbidden_for_non_admin(client, admin_db):
    """Non-admin users get 403 on analysis endpoints."""
    with patch("app.routes.admin.get_operator_from_request", return_value="Miguel"), \
         patch("app.routes.admin.is_admin", return_value=False):
        resp = await client.post(
            "/admin/analysis/run",
            json={"period_start": "2026-03-01", "period_end": "2026-03-07"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_analysis_trigger_returns_run_id(client, admin_db):
    """Admin can trigger analysis and gets run_id back."""
    with patch("app.routes.admin.get_operator_from_request", return_value="Caio"), \
         patch("app.routes.admin.is_admin", return_value=True), \
         patch("app.routes.admin.get_db") as mock_get_db:

        mock_get_db.return_value = admin_db

        # Mock the background task to not actually run
        with patch("app.routes.admin.asyncio.create_task"):
            resp = await client.post(
                "/admin/analysis/run",
                json={"period_start": "2026-03-01", "period_end": "2026-03-07"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "running"
    assert data["period_start"] == "2026-03-01"
    assert data["period_end"] == "2026-03-07"


@pytest.mark.asyncio
async def test_admin_results_returns_latest_run(client, admin_db):
    """Results endpoint returns latest completed run."""
    # Insert a completed run with digest
    await admin_db.execute(
        """INSERT INTO analysis_runs (period_start, period_end, status, total_conversations, total_operators, completed_at)
           VALUES ('2026-03-01', '2026-03-07', 'completed', 5, 2, '2026-03-07 23:00:00')"""
    )
    await admin_db.execute(
        """INSERT INTO operator_digests (analysis_run_id, operator_name, summary, patterns_json, factual_issues_json, salvageable_sales_json, metrics_json)
           VALUES (1, 'Miguel', 'Piloto automatico total', '[]', '[]', '[]', '{"total_conversations": 3}')"""
    )
    await admin_db.commit()

    with patch("app.routes.admin.get_operator_from_request", return_value="Caio"), \
         patch("app.routes.admin.is_admin", return_value=True), \
         patch("app.routes.admin.get_db") as mock_get_db:

        async def return_db():
            return admin_db

        mock_get_db.side_effect = return_db

        resp = await client.get("/admin/analysis/results")

    assert resp.status_code == 200
    data = resp.json()
    assert data["run"]["id"] == 1
    assert data["run"]["status"] == "completed"
    assert len(data["operator_digests"]) == 1
    assert data["operator_digests"][0]["operator_name"] == "Miguel"


@pytest.mark.asyncio
async def test_admin_coaching_page_redirects_non_admin(client, admin_db):
    """Non-admin visiting /admin/coaching gets redirected."""
    with patch("app.routes.admin.get_operator_from_request", return_value="Miguel"), \
         patch("app.routes.admin.is_admin", return_value=False):
        resp = await client.get("/admin/coaching", follow_redirects=False)
    assert resp.status_code == 307 or resp.status_code == 302
