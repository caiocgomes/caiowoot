import os
from unittest.mock import patch

import pytest
import pytest_asyncio
import aiosqlite

import app.database as db_module


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(db_module.SCHEMA)
    await conn.commit()

    class NonClosing:
        def __init__(self, c):
            self._conn = c
        async def close(self):
            pass
        def __getattr__(self, name):
            return getattr(self._conn, name)

    wrapper = NonClosing(conn)

    async def mock_get_db():
        return wrapper

    with patch("app.services.operator_profile.get_db", mock_get_db):
        yield conn

    await conn.close()


@pytest.mark.asyncio
async def test_get_profile_returns_none_when_empty(db):
    from app.services.operator_profile import get_profile

    profile = await get_profile("Caio")

    assert profile is None


@pytest.mark.asyncio
async def test_upsert_and_get_profile(db):
    from app.services.operator_profile import get_profile, upsert_profile

    await upsert_profile("João", "João Silva", "Trabalho na equipe do Caio, não sou o dono dos cursos.")

    profile = await get_profile("João")
    assert profile is not None
    assert profile["display_name"] == "João Silva"
    assert profile["context"] == "Trabalho na equipe do Caio, não sou o dono dos cursos."


@pytest.mark.asyncio
async def test_upsert_profile_overwrites(db):
    from app.services.operator_profile import get_profile, upsert_profile

    await upsert_profile("Caio", "Caio G", "Versão 1")
    await upsert_profile("Caio", "Caio Gomes", "Versão 2")

    profile = await get_profile("Caio")
    assert profile["display_name"] == "Caio Gomes"
    assert profile["context"] == "Versão 2"


@pytest.mark.asyncio
async def test_profiles_are_isolated_per_operator(db):
    from app.services.operator_profile import get_profile, upsert_profile

    await upsert_profile("Caio", "Caio", "Sou o dono")
    await upsert_profile("João", "João", "Sou da equipe")

    caio = await get_profile("Caio")
    joao = await get_profile("João")

    assert caio["context"] == "Sou o dono"
    assert joao["context"] == "Sou da equipe"
