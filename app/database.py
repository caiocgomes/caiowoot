import os
from pathlib import Path

import aiosqlite
import chromadb

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL UNIQUE,
    contact_name TEXT,
    status TEXT DEFAULT 'active',
    last_read_at TIMESTAMP,
    funnel_product TEXT,
    funnel_stage TEXT,
    is_qualified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    origin_campaign_id INTEGER
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    evolution_message_id TEXT UNIQUE,
    direction TEXT NOT NULL,
    content TEXT NOT NULL,
    media_url TEXT,
    media_type TEXT,
    sent_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    trigger_message_id INTEGER NOT NULL REFERENCES messages(id),
    draft_text TEXT NOT NULL,
    justification TEXT,
    status TEXT DEFAULT 'pending',
    draft_group_id TEXT,
    variation_index INTEGER,
    approach TEXT,
    prompt_hash TEXT,
    operator_instruction TEXT,
    situation_summary TEXT,
    suggested_attachment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS edit_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    customer_message TEXT NOT NULL,
    original_draft TEXT NOT NULL,
    final_message TEXT NOT NULL,
    was_edited BOOLEAN NOT NULL,
    operator_instruction TEXT,
    all_drafts_json TEXT,
    selected_draft_index INTEGER,
    prompt_hash TEXT,
    regeneration_count INTEGER DEFAULT 0,
    situation_summary TEXT,
    strategic_annotation TEXT,
    validated BOOLEAN DEFAULT 0,
    rejected BOOLEAN DEFAULT 0,
    attachment_filename TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learned_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text TEXT NOT NULL,
    source_edit_pair_id INTEGER REFERENCES edit_pairs(id),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operator_profiles (
    operator_name TEXT PRIMARY KEY,
    display_name TEXT,
    context TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    content TEXT NOT NULL,
    send_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'pending',
    cancelled_reason TEXT,
    cancelled_by_message_id INTEGER,
    draft_id INTEGER,
    draft_group_id TEXT,
    selected_draft_index INTEGER,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    total_conversations INTEGER DEFAULT 0,
    total_operators INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_run_id INTEGER NOT NULL,
    conversation_id INTEGER NOT NULL,
    operator_name TEXT,
    engagement_level TEXT,
    sale_status TEXT,
    recovery_potential TEXT,
    recovery_suggestion TEXT,
    factual_issues_json TEXT,
    overall_assessment TEXT,
    metrics_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operator_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_run_id INTEGER NOT NULL,
    operator_name TEXT NOT NULL,
    summary TEXT,
    patterns_json TEXT,
    factual_issues_json TEXT,
    salvageable_sales_json TEXT,
    metrics_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    base_message TEXT NOT NULL DEFAULT '',
    image_path TEXT,
    min_interval INTEGER DEFAULT 60,
    max_interval INTEGER DEFAULT 180,
    next_send_at TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaign_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    phone_number TEXT NOT NULL,
    name TEXT,
    status TEXT DEFAULT 'pending',
    variation_id INTEGER,
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaign_variations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    variation_index INTEGER NOT NULL,
    variation_text TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
"""

MIGRATIONS = [
    ("situation_summary_on_drafts",
     "ALTER TABLE drafts ADD COLUMN situation_summary TEXT"),
    ("situation_summary_on_edit_pairs",
     "ALTER TABLE edit_pairs ADD COLUMN situation_summary TEXT"),
    ("strategic_annotation_on_edit_pairs",
     "ALTER TABLE edit_pairs ADD COLUMN strategic_annotation TEXT"),
    ("validated_on_edit_pairs",
     "ALTER TABLE edit_pairs ADD COLUMN validated BOOLEAN DEFAULT 0"),
    ("rejected_on_edit_pairs",
     "ALTER TABLE edit_pairs ADD COLUMN rejected BOOLEAN DEFAULT 0"),
    ("learned_rules_table", """
        CREATE TABLE IF NOT EXISTS learned_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_text TEXT NOT NULL,
            source_edit_pair_id INTEGER REFERENCES edit_pairs(id),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("sent_by_on_messages",
     "ALTER TABLE messages ADD COLUMN sent_by TEXT"),
    ("attachment_filename_on_edit_pairs",
     "ALTER TABLE edit_pairs ADD COLUMN attachment_filename TEXT"),
    ("prompt_config_table", """
        CREATE TABLE IF NOT EXISTS prompt_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("operator_profiles_table", """
        CREATE TABLE IF NOT EXISTS operator_profiles (
            operator_name TEXT PRIMARY KEY,
            display_name TEXT,
            context TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("last_read_at_on_conversations",
     "ALTER TABLE conversations ADD COLUMN last_read_at TIMESTAMP"),
    ("funnel_product_on_conversations",
     "ALTER TABLE conversations ADD COLUMN funnel_product TEXT"),
    ("funnel_stage_on_conversations",
     "ALTER TABLE conversations ADD COLUMN funnel_stage TEXT"),
    ("analysis_runs_table", """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            total_conversations INTEGER DEFAULT 0,
            total_operators INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """),
    ("conversation_assessments_table", """
        CREATE TABLE IF NOT EXISTS conversation_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
            conversation_id INTEGER NOT NULL REFERENCES conversations(id),
            operator_name TEXT,
            engagement_level TEXT,
            sale_status TEXT,
            recovery_potential TEXT,
            recovery_suggestion TEXT,
            factual_issues_json TEXT,
            overall_assessment TEXT,
            metrics_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("operator_digests_table", """
        CREATE TABLE IF NOT EXISTS operator_digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
            operator_name TEXT NOT NULL,
            summary TEXT,
            patterns_json TEXT,
            factual_issues_json TEXT,
            salvageable_sales_json TEXT,
            metrics_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("scheduled_sends_table", """
        CREATE TABLE IF NOT EXISTS scheduled_sends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id),
            content TEXT NOT NULL,
            send_at TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            cancelled_reason TEXT,
            cancelled_by_message_id INTEGER,
            draft_id INTEGER,
            draft_group_id TEXT,
            selected_draft_index INTEGER,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP
        )
    """),
    ("scheduled_sends_status_send_at_index",
     "CREATE INDEX IF NOT EXISTS idx_scheduled_sends_status_send_at ON scheduled_sends (status, send_at)"),
    ("suggested_attachment_on_drafts",
     "ALTER TABLE drafts ADD COLUMN suggested_attachment TEXT"),
    ("campaigns_table", """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            base_message TEXT NOT NULL DEFAULT '',
            image_path TEXT,
            min_interval INTEGER DEFAULT 60,
            max_interval INTEGER DEFAULT 180,
            next_send_at TIMESTAMP,
            consecutive_failures INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("campaign_contacts_table", """
        CREATE TABLE IF NOT EXISTS campaign_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
            phone_number TEXT NOT NULL,
            name TEXT,
            status TEXT DEFAULT 'pending',
            variation_id INTEGER,
            error_message TEXT,
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("campaign_variations_table", """
        CREATE TABLE IF NOT EXISTS campaign_variations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
            variation_index INTEGER NOT NULL,
            variation_text TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0
        )
    """),
    ("origin_campaign_id_on_conversations",
     "ALTER TABLE conversations ADD COLUMN origin_campaign_id INTEGER"),
    ("idx_messages_conversation_id",
     "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"),
    ("idx_drafts_conv_status",
     "CREATE INDEX IF NOT EXISTS idx_drafts_conv_status ON drafts(conversation_id, status)"),
    ("idx_edit_pairs_conversation_id",
     "CREATE INDEX IF NOT EXISTS idx_edit_pairs_conversation_id ON edit_pairs(conversation_id)"),
    ("idx_campaign_contacts_camp_status",
     "CREATE INDEX IF NOT EXISTS idx_campaign_contacts_camp_status ON campaign_contacts(campaign_id, status)"),
    ("campaign_variations_is_active",
     "ALTER TABLE campaign_variations ADD COLUMN is_active INTEGER DEFAULT 1"),
    ("conversations_is_qualified",
     "ALTER TABLE conversations ADD COLUMN is_qualified INTEGER DEFAULT 0"),
    ("conversations_existing_qualified",
     "UPDATE conversations SET is_qualified = 1 WHERE is_qualified = 0"),
]

_chroma_client = None
_chroma_collection = None


def get_chroma_collection():
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        db_path = Path(settings.database_path)
        chroma_path = str(db_path.parent / "chroma")
        _chroma_client = chromadb.PersistentClient(path=chroma_path)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name="situations",
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


async def get_db() -> aiosqlite.Connection:
    """Create a standalone DB connection. Used by background tasks that run outside request context."""
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    return db


async def get_db_connection():
    """FastAPI dependency that provides a DB connection per request."""
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def _run_migrations(db: aiosqlite.Connection):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            name TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for name, sql in MIGRATIONS:
        row = await db.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,))
        if await row.fetchone():
            continue
        try:
            await db.execute(sql)
            await db.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate column" in err_msg:
                await db.execute("INSERT OR IGNORE INTO _migrations (name) VALUES (?)", (name,))
            else:
                import logging
                logging.getLogger(__name__).error("Migration '%s' failed: %s", name, e)
                raise


async def init_db():
    db_path = Path(settings.database_path)
    os.makedirs(db_path.parent, exist_ok=True)
    os.makedirs(db_path.parent / "prompts", exist_ok=True)
    os.makedirs(db_path.parent / "attachments", exist_ok=True)
    db = await get_db()
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(SCHEMA)
        await _run_migrations(db)
        await db.commit()
    finally:
        await db.close()

    if settings.database_path != ":memory:":
        get_chroma_collection()
