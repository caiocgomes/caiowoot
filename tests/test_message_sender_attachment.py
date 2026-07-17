"""Ordenação de I/O em send_and_record com anexo.

Contrato (fase GREEN): a gravação do arquivo em disco NÃO pode ocorrer dentro
da transação de escrita — o evento 'write_file' deve vir antes do primeiro
'insert' ou depois do 'commit', nunca entre os dois.

Hoje: red — message_sender grava o arquivo entre o INSERT em messages e o
commit, segurando a transação durante I/O de disco.
"""

import pathlib

import pytest

from app.config import settings
from app.services.message_sender import send_and_record


class _EventSpyConn:
    """Espião de conexão: registra 'insert' e 'commit' numa sequência de eventos."""

    def __init__(self, conn, events):
        self._conn = conn
        self._events = events

    async def execute(self, sql, *args, **kwargs):
        if sql.lstrip().lower().startswith("insert"):
            self._events.append("insert")
        return await self._conn.execute(sql, *args, **kwargs)

    async def commit(self):
        self._events.append("commit")
        await self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.mark.asyncio
async def test_gravacao_de_arquivo_fora_da_transacao(db, mock_evolution_api, monkeypatch, tmp_path):
    """send_and_record com file_bytes: 'write_file' não pode aparecer entre o primeiro 'insert' e o 'commit'."""
    # Redireciona o diretório de anexos pra fora do repositório
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "caiowoot.db"))

    await db.execute(
        "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
    )
    await db.commit()

    events = []

    def fake_write_bytes(self, data):
        events.append("write_file")
        return len(data)

    monkeypatch.setattr(pathlib.Path, "write_bytes", fake_write_bytes)

    spy = _EventSpyConn(db, events)

    result = await send_and_record(
        spy,
        1,
        "Segue a foto",
        file_bytes=b"bytes-de-imagem-fake",
        filename="foto.jpg",
        content_type="image/jpeg",
    )

    assert result["message_id"] is not None
    assert "write_file" in events, (
        "instrumentação não capturou a gravação do arquivo em disco — "
        f"eventos registrados: {events}"
    )

    first_insert = events.index("insert")
    commit_idx = events.index("commit", first_insert)
    entre_txn = events[first_insert + 1 : commit_idx]
    assert "write_file" not in entre_txn, (
        "gravação de arquivo aconteceu dentro da transação (entre o primeiro "
        f"INSERT e o commit); sequência de eventos: {events}"
    )
