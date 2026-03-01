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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


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
        except Exception:
            pass  # Column/table already exists from SCHEMA


async def init_db():
    db_path = Path(settings.database_path)
    os.makedirs(db_path.parent, exist_ok=True)
    os.makedirs(db_path.parent / "prompts", exist_ok=True)
    os.makedirs(db_path.parent / "attachments", exist_ok=True)
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await _run_migrations(db)
        await db.commit()
    finally:
        await db.close()

    if settings.database_path != ":memory:":
        get_chroma_collection()
