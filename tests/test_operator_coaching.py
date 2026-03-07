import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import *  # noqa: F401, F403


def _make_analysis_result(conv_id, operator, engagement="medium", sale_status="active", recovery="none"):
    return {
        "conversation_id": conv_id,
        "operator_name": operator,
        "contact_name": f"Cliente {conv_id}",
        "engagement_level": engagement,
        "engagement_notes": "notas",
        "sale_status": sale_status,
        "recovery_potential": recovery,
        "recovery_suggestion": "retomar conversa" if recovery != "none" else None,
        "factual_issues": [],
        "overall_assessment": "avaliacao",
        "metrics": {
            "total_messages": 3,
            "draft_acceptance_rate": 80.0,
            "avg_regeneration": 0,
            "response_times": [5.0],
            "approach_counts": {"direta": 2},
        },
    }


def _make_digest_response():
    return MagicMock(
        content=[
            MagicMock(
                text=json.dumps(
                    {
                        "summary": "Operador no piloto automatico.",
                        "patterns": [
                            {
                                "pattern": "Aceita todos os drafts",
                                "examples": ["Conv com Cliente 1: aceitou draft generico"],
                                "suggestion": "Personalizar respostas",
                            }
                        ],
                        "factual_issues_highlight": [],
                        "salvageable_sales": [
                            {
                                "conversation_id": 2,
                                "contact_name": "Cliente 2",
                                "situation": "Parou de responder",
                                "suggestion": "Mandar follow-up",
                                "priority": "high",
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
            )
        ]
    )


@pytest.mark.asyncio
async def test_run_analysis_lifecycle(db):
    """run_analysis creates run record, processes conversations, generates digests."""
    # Setup conversations with messages
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5511111', 'Cliente 1')")
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5522222', 'Cliente 2')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) VALUES (1, 'inbound', 'Oi', NULL, '2026-03-01 10:00:00')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) VALUES (1, 'outbound', 'Ola!', 'Miguel', '2026-03-01 10:05:00')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) VALUES (2, 'inbound', 'Bom dia', NULL, '2026-03-01 11:00:00')"
    )
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) VALUES (2, 'outbound', 'Oi!', 'Miguel', '2026-03-01 11:10:00')"
    )
    # Apply migrations for analysis tables
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

    mock_analysis = AsyncMock(side_effect=[
        _make_analysis_result(1, "Miguel"),
        _make_analysis_result(2, "Miguel", sale_status="cooling", recovery="high"),
    ])

    mock_digest_resp = _make_digest_response()
    mock_sonnet = AsyncMock()
    mock_sonnet.messages.create = AsyncMock(return_value=mock_digest_resp)

    with patch("app.services.operator_coaching.analyze_conversation", mock_analysis), \
         patch("app.services.operator_coaching.anthropic.AsyncAnthropic", return_value=mock_sonnet), \
         patch("app.services.operator_coaching.get_db", return_value=db.__class__.__new__(db.__class__)):
        # We need get_db to return our test db
        from app.services.operator_coaching import _process_analysis

        # Create run record
        cursor = await db.execute(
            "INSERT INTO analysis_runs (period_start, period_end, status) VALUES ('2026-03-01', '2026-03-07', 'running')"
        )
        run_id = cursor.lastrowid
        await db.commit()

        await _process_analysis(db, run_id, "2026-03-01", "2026-03-07")

    # Verify run completed
    row = await db.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,))
    run = await row.fetchone()
    assert run["status"] == "completed"
    assert run["total_conversations"] == 2
    assert run["total_operators"] == 1

    # Verify assessments saved
    rows = await db.execute("SELECT COUNT(*) as c FROM conversation_assessments WHERE analysis_run_id = ?", (run_id,))
    count = await rows.fetchone()
    assert count["c"] == 2

    # Verify operator digest saved
    rows = await db.execute(
        "SELECT * FROM operator_digests WHERE analysis_run_id = ? AND operator_name = 'Miguel'", (run_id,)
    )
    digest = await rows.fetchone()
    assert digest is not None
    assert "piloto" in digest["summary"].lower()
    patterns = json.loads(digest["patterns_json"])
    assert len(patterns) == 1
    salvageable = json.loads(digest["salvageable_sales_json"])
    assert len(salvageable) == 1
    assert salvageable[0]["priority"] == "high"


@pytest.mark.asyncio
async def test_unanswered_conversations_detected(db):
    """Conversations with inbound but no outbound in period are flagged."""
    await db.execute("INSERT INTO conversations (phone_number, contact_name) VALUES ('5511111', 'Ignorado')")
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, sent_by, created_at) VALUES (1, 'inbound', 'Alguem ai?', NULL, '2026-03-05 10:00:00')"
    )
    # Apply migrations
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

    from app.services.operator_coaching import _process_analysis

    cursor = await db.execute(
        "INSERT INTO analysis_runs (period_start, period_end, status) VALUES ('2026-03-01', '2026-03-07', 'running')"
    )
    run_id = cursor.lastrowid
    await db.commit()

    await _process_analysis(db, run_id, "2026-03-01", "2026-03-07")

    # Verify unanswered entry
    rows = await db.execute(
        "SELECT * FROM operator_digests WHERE analysis_run_id = ? AND operator_name = '__unanswered__'",
        (run_id,),
    )
    unanswered = await rows.fetchone()
    assert unanswered is not None
    data = json.loads(unanswered["salvageable_sales_json"])
    assert len(data) == 1
    assert data[0]["contact_name"] == "Ignorado"
