"""Testes RED: índices de performance criados via migrations.

Contrato da fase GREEN (refactor-velocidade):
- init_db deve criar os índices idx_messages_conv_created,
  idx_messages_conv_dir_created, idx_scheduled_sends_conv_status,
  idx_drafts_group e idx_campaign_contacts_phone.
- O índice idx_messages_conversation_id deve ser dropado por redundância
  (coberto pelos índices compostos que começam por conversation_id).
"""

import aiosqlite
import pytest

from app.config import settings
from app.database import init_db


async def _index_names(db_path: str) -> set[str]:
    """Retorna o conjunto de nomes de índices presentes no arquivo SQLite."""
    conn = await aiosqlite.connect(db_path)
    try:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}
    finally:
        await conn.close()


async def _run_init_db_on_tmp_file(tmp_path, monkeypatch) -> set[str]:
    """Roda init_db contra um arquivo em tmp_path e retorna os índices criados."""
    db_file = str(tmp_path / "caiowoot_test.db")
    monkeypatch.setattr(settings, "database_path", db_file)
    # Evita instanciar ChromaDB real (init_db chama get_chroma_collection
    # quando database_path não é :memory:)
    monkeypatch.setattr("app.database.get_chroma_collection", lambda: None)

    await init_db()
    return await _index_names(db_file)


@pytest.mark.asyncio
async def test_init_db_creates_performance_indexes(tmp_path, monkeypatch):
    """init_db cria os índices compostos de performance nas migrations."""
    names = await _run_init_db_on_tmp_file(tmp_path, monkeypatch)

    expected = {
        "idx_messages_conv_created",
        "idx_messages_conv_dir_created",
        "idx_scheduled_sends_conv_status",
        "idx_drafts_group",
        "idx_campaign_contacts_phone",
    }
    missing = expected - names
    assert not missing, (
        f"Índices de performance ausentes após init_db: {sorted(missing)}. "
        "Contrato: as migrations em app/database.py devem criá-los."
    )


@pytest.mark.asyncio
async def test_init_db_drops_redundant_messages_index(tmp_path, monkeypatch):
    """idx_messages_conversation_id não deve existir (redundante com os compostos)."""
    names = await _run_init_db_on_tmp_file(tmp_path, monkeypatch)

    assert "idx_messages_conversation_id" not in names, (
        "idx_messages_conversation_id deveria ser dropado por redundância: "
        "os índices compostos idx_messages_conv_created e "
        "idx_messages_conv_dir_created já começam por conversation_id."
    )
