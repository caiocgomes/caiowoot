"""Testes do endpoint /rewarm/suggested-date: default varia por dia da semana."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from tests.conftest import *  # noqa: F401, F403


TZ = ZoneInfo("America/Sao_Paulo")


def _mock_today(year: int, month: int, day: int):
    """Retorna um context manager que faz now_local() e também o now_local() dentro
    do módulo de rotas retornarem o dia especificado."""
    fake_now = datetime(year, month, day, 12, 0, tzinfo=TZ)
    return patch("app.routes.rewarm.now_local", return_value=fake_now)


@pytest.mark.asyncio
async def test_suggested_date_on_monday_returns_friday(client, db):
    # 2026-04-20 é segunda. Sexta passada: 2026-04-17.
    with _mock_today(2026, 4, 20):
        resp = await client.get("/rewarm/suggested-date")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"date": "2026-04-17", "label": "sexta-feira"}


@pytest.mark.asyncio
async def test_suggested_date_on_tuesday_returns_yesterday(client, db):
    # 2026-04-21 é terça. Ontem: 2026-04-20 (segunda).
    with _mock_today(2026, 4, 21):
        resp = await client.get("/rewarm/suggested-date")
    assert resp.status_code == 200
    assert resp.json() == {"date": "2026-04-20", "label": "segunda-feira"}


@pytest.mark.asyncio
async def test_suggested_date_on_friday_returns_yesterday(client, db):
    # 2026-04-17 é sexta. Ontem: 2026-04-16 (quinta).
    with _mock_today(2026, 4, 17):
        resp = await client.get("/rewarm/suggested-date")
    assert resp.json() == {"date": "2026-04-16", "label": "quinta-feira"}


@pytest.mark.asyncio
async def test_suggested_date_on_saturday_returns_friday(client, db):
    # 2026-04-18 é sábado. Ontem: sexta 17.
    with _mock_today(2026, 4, 18):
        resp = await client.get("/rewarm/suggested-date")
    assert resp.json() == {"date": "2026-04-17", "label": "sexta-feira"}


@pytest.mark.asyncio
async def test_suggested_date_on_sunday_returns_saturday(client, db):
    # 2026-04-19 é domingo. Ontem: sábado 18.
    with _mock_today(2026, 4, 19):
        resp = await client.get("/rewarm/suggested-date")
    assert resp.json() == {"date": "2026-04-18", "label": "sábado"}
