"""Testes RED: limite de mensagens no histórico do prompt builder.

Contrato da fase GREEN (refactor-velocidade):
- app/services/prompt_builder.py expõe a constante MAX_HISTORY_MESSAGES = 100.
- build_conversation_history carrega no máximo as últimas 100 mensagens
  da conversa, mantendo ordem cronológica ASC (com 150 mensagens, a
  primeira linha do histórico é a mensagem 51 e a última é a 150).

Hoje: red — build_conversation_history carrega todas as mensagens.
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.services.prompt_builder as prompt_builder


def _utc_iso(dt: datetime) -> str:
    """Converte para ISO UTC naive (mesmo formato do CURRENT_TIMESTAMP do SQLite)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat()


async def _seed_conversation_with_messages(db, total: int) -> None:
    """Insere uma conversa com `total` mensagens de created_at crescentes distintos."""
    await db.execute(
        "INSERT INTO conversations (phone_number) VALUES ('5511999999999')"
    )
    base = datetime.now(timezone.utc) - timedelta(minutes=total + 5)
    for i in range(1, total + 1):
        ts = _utc_iso(base + timedelta(minutes=i))
        await db.execute(
            "INSERT INTO messages (conversation_id, evolution_message_id, direction, content, created_at) "
            "VALUES (1, ?, 'inbound', ?, ?)",
            (f"msg-{i}", f"mensagem {i:03d}", ts),
        )
    await db.commit()


@pytest.mark.asyncio
async def test_history_limited_to_last_100_messages_in_asc_order(db):
    """Com 150 mensagens, o histórico contém só as últimas 100, em ordem ASC."""
    await _seed_conversation_with_messages(db, total=150)

    history, _, _ = await prompt_builder.build_conversation_history(db, 1)
    lines = history.strip().split("\n")

    assert len(lines) == 100, (
        f"Histórico deveria conter só as últimas 100 mensagens, veio com {len(lines)}. "
        "Contrato: MAX_HISTORY_MESSAGES = 100 aplicado na query."
    )
    assert "mensagem 051" in lines[0], (
        "Primeira linha do histórico deveria ser a mensagem 51 "
        f"(ordem cronológica ASC preservada), veio: {lines[0]!r}"
    )
    assert "mensagem 150" in lines[-1], (
        "Última linha do histórico deveria ser a mensagem 150 (a mais recente), "
        f"veio: {lines[-1]!r}"
    )


def test_max_history_messages_constant_is_100():
    """prompt_builder expõe MAX_HISTORY_MESSAGES = 100."""
    # Símbolo novo: resolvido via getattr para falhar por assert, não por import
    limit = getattr(prompt_builder, "MAX_HISTORY_MESSAGES", None)
    assert limit == 100, (
        "app/services/prompt_builder.py deve expor a constante "
        f"MAX_HISTORY_MESSAGES = 100 (valor atual: {limit!r})"
    )
