"""Testes RED: PRAGMAs obrigatórios nas factories de conexão de app.database.

Contrato novo (fase GREEN): toda conexão criada por get_db() e
get_db_connection() deve sair configurada com:

- busy_timeout = 10000  (escritor concorrente espera o lock em vez de
  estourar 'database is locked')
- synchronous = 1 (NORMAL — nível adequado a WAL, menos fsyncs por commit)
- foreign_keys = 1 (integridade referencial ligada)

Hoje as factories não executam PRAGMA nenhum: busy_timeout fica no default
do sqlite3 do Python (5000ms via timeout=5.0 do connect), synchronous fica
em 2 (FULL) e foreign_keys em 0. Os testes falham por assert de comportamento.
"""

import pytest

from app.config import settings
from app.database import get_db, get_db_connection

PRAGMAS_ESPERADOS = {
    "busy_timeout": 10000,
    "synchronous": 1,
    "foreign_keys": 1,
}


async def _le_pragmas(conn) -> dict[str, int]:
    """Lê os PRAGMAs relevantes direto da conexão entregue pela factory."""
    valores = {}
    for nome in PRAGMAS_ESPERADOS:
        cursor = await conn.execute(f"PRAGMA {nome}")
        row = await cursor.fetchone()
        valores[nome] = row[0]
    return valores


@pytest.mark.asyncio
async def test_get_db_configura_pragmas(tmp_path, monkeypatch):
    """get_db() deve entregar conexão com busy_timeout, synchronous e foreign_keys corretos."""
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "pragmas.db"))

    conn = await get_db()
    try:
        valores = await _le_pragmas(conn)
    finally:
        await conn.close()

    assert valores == PRAGMAS_ESPERADOS, (
        "get_db() entregou conexão sem os PRAGMAs do contrato novo: "
        f"esperado {PRAGMAS_ESPERADOS}, obtido {valores}"
    )


@pytest.mark.asyncio
async def test_get_db_connection_configura_pragmas(tmp_path, monkeypatch):
    """Uma iteração de get_db_connection() deve entregar conexão com os mesmos PRAGMAs."""
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "pragmas.db"))

    gen = get_db_connection()
    conn = await gen.__anext__()
    try:
        valores = await _le_pragmas(conn)
    finally:
        await gen.aclose()

    assert valores == PRAGMAS_ESPERADOS, (
        "get_db_connection() entregou conexão sem os PRAGMAs do contrato novo: "
        f"esperado {PRAGMAS_ESPERADOS}, obtido {valores}"
    )
