import os
from pathlib import Path

import aiosqlite

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db_path = Path(settings.database_path)
    os.makedirs(db_path.parent, exist_ok=True)
    os.makedirs(db_path.parent / "prompts", exist_ok=True)
    os.makedirs(db_path.parent / "attachments", exist_ok=True)
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()
