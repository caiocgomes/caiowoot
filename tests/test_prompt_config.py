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

    with patch("app.services.prompt_config.get_db", mock_get_db):
        yield conn

    await conn.close()


@pytest.mark.asyncio
async def test_get_all_prompts_returns_defaults_when_empty(db):
    from app.services.prompt_config import get_all_prompts, PROMPT_DEFAULTS

    prompts = await get_all_prompts()

    assert isinstance(prompts, dict)
    for key in PROMPT_DEFAULTS:
        assert key in prompts
        assert prompts[key] == PROMPT_DEFAULTS[key]


@pytest.mark.asyncio
async def test_update_prompts_persists_values(db):
    from app.services.prompt_config import get_all_prompts, update_prompts

    await update_prompts({"postura": "Nova postura customizada"})
    prompts = await get_all_prompts()

    assert prompts["postura"] == "Nova postura customizada"


@pytest.mark.asyncio
async def test_update_prompts_partial_update(db):
    from app.services.prompt_config import get_all_prompts, update_prompts, PROMPT_DEFAULTS

    await update_prompts({"tom": "Tom diferente"})
    prompts = await get_all_prompts()

    assert prompts["tom"] == "Tom diferente"
    assert prompts["postura"] == PROMPT_DEFAULTS["postura"]


@pytest.mark.asyncio
async def test_reset_prompt_falls_back_to_default(db):
    from app.services.prompt_config import get_all_prompts, update_prompts, reset_prompt, PROMPT_DEFAULTS

    await update_prompts({"postura": "Customizada"})
    prompts = await get_all_prompts()
    assert prompts["postura"] == "Customizada"

    await reset_prompt("postura")
    prompts = await get_all_prompts()
    assert prompts["postura"] == PROMPT_DEFAULTS["postura"]


@pytest.mark.asyncio
async def test_update_prompts_upsert_overwrites(db):
    from app.services.prompt_config import get_all_prompts, update_prompts

    await update_prompts({"regras": "Versão 1"})
    await update_prompts({"regras": "Versão 2"})
    prompts = await get_all_prompts()

    assert prompts["regras"] == "Versão 2"


@pytest.mark.asyncio
async def test_defaults_contain_all_expected_keys():
    from app.services.prompt_config import PROMPT_DEFAULTS

    expected_keys = {
        "postura", "tom", "regras",
        "approach_direta", "approach_consultiva", "approach_casual",
        "summary_prompt", "annotation_prompt",
    }
    assert set(PROMPT_DEFAULTS.keys()) == expected_keys
