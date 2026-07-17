"""Testes RED: write lock do SQLite atravessando await de rede na geração de drafts.

Bug real: build_prompt_parts (app/services/prompt_builder.py:328) executa
UPDATE conversations SET funnel_... na conexão do draft_engine, mas o commit
só acontece em generate_drafts DEPOIS de aguardar as 3 chamadas Haiku.
A transação de escrita fica aberta durante o await de rede e segura o write
lock do arquivo, bloqueando qualquer escritor concorrente (webhook, scheduler,
operador enviando mensagem).

Contrato novo (fase GREEN): o UPDATE de funil deve estar commitado (e o lock
liberado) ANTES das chamadas LLM. Escritores concorrentes não podem estourar
'database is locked' nem esperar a geração inteira terminar.

Estes testes usam banco em ARQUIVO (tmp_path) de propósito: o lock de arquivo
é o comportamento sob teste; a fixture db do conftest (conexão compartilhada
em memória) não reproduz o problema.
"""

import asyncio
import contextlib
import time
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
import pytest_asyncio

import app.database as db_module
from app.config import settings
from app.database import init_db
from app.services.draft_engine import generate_drafts

# Resumo que dispara o UPDATE de funil dentro de build_prompt_parts
SUMMARY_COM_FUNIL = {"summary": "s", "product": "curso-cdo", "stage": "decided"}


@pytest_asyncio.fixture
async def file_db_path(tmp_path, monkeypatch):
    """Banco em arquivo real com schema inicializado e uma conversa semeada."""
    db_path = tmp_path / "locks.db"
    monkeypatch.setattr(settings, "database_path", str(db_path))
    # init_db sobe cliente ChromaDB real quando o banco não é :memory: — evita isso
    monkeypatch.setattr(db_module, "get_chroma_collection", lambda: MagicMock())
    await init_db()

    conn = await aiosqlite.connect(str(db_path))
    try:
        await conn.execute(
            "INSERT INTO conversations (phone_number, contact_name) VALUES ('5511999999999', 'Maria')"
        )
        await conn.execute(
            "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
            "VALUES (1, 'msg-1', 'inbound', 'Quero saber sobre os cursos')"
        )
        await conn.commit()
    finally:
        await conn.close()

    yield db_path


def _patches_draft_engine(db_path, call_haiku_mock):
    """Patches mínimos para rodar generate_drafts contra o arquivo real.

    Diferente do conftest, get_db é patchado com função que abre conexão
    REAL nova para o arquivo — cada chamada ganha sua própria conexão,
    como em produção. draft_engine importa call_haiku como _call_haiku,
    então o patch é em app.services.draft_engine._call_haiku.
    """

    async def get_db_arquivo():
        conn = await aiosqlite.connect(str(db_path))
        conn.row_factory = aiosqlite.Row
        return conn

    stack = ExitStack()
    stack.enter_context(patch("app.services.draft_engine.get_db", get_db_arquivo))
    stack.enter_context(patch("app.services.draft_engine._call_haiku", call_haiku_mock))
    # build_prompt_parts roda no namespace de prompt_builder — patches lá
    stack.enter_context(
        patch(
            "app.services.prompt_builder.generate_situation_summary",
            new_callable=AsyncMock,
            return_value=dict(SUMMARY_COM_FUNIL),
        )
    )
    stack.enter_context(patch("app.services.prompt_builder.retrieve_similar", return_value=[]))
    stack.enter_context(
        patch(
            "app.services.prompt_builder.get_active_rules",
            new_callable=AsyncMock,
            return_value=[],
        )
    )
    stack.enter_context(patch("app.services.draft_engine.save_prompt", return_value="testhash123"))
    mock_ws = stack.enter_context(patch("app.websocket_manager.manager"))
    mock_ws.broadcast = AsyncMock()
    return stack


@pytest.mark.asyncio
async def test_funil_commitado_antes_do_llm(file_db_path):
    """Enquanto o Haiku está em voo, outra conexão deve conseguir escrever no banco
    E já enxergar o funil novo (prova de que o commit veio antes da chamada LLM)."""
    entrou_no_llm = asyncio.Event()
    libera_llm = asyncio.Event()

    async def haiku_bloqueante(*args, **kwargs):
        entrou_no_llm.set()
        await libera_llm.wait()
        return ("rascunho de teste", "justificativa de teste", None)

    mock_haiku = AsyncMock(side_effect=haiku_bloqueante)

    task = None
    conn2 = None
    with _patches_draft_engine(file_db_path, mock_haiku):
        try:
            task = asyncio.create_task(generate_drafts(1, 1))
            # Espera o mock sinalizar que as chamadas LLM começaram
            await asyncio.wait_for(entrou_no_llm.wait(), timeout=10)

            # Segunda conexão independente ao MESMO arquivo, timeout curto:
            # se a transação do funil ainda estiver aberta, esta escrita estoura.
            conn2 = await aiosqlite.connect(str(file_db_path))
            conn2.row_factory = aiosqlite.Row
            await conn2.execute("PRAGMA busy_timeout = 500")

            try:
                await conn2.execute(
                    "UPDATE conversations SET contact_name = 'Concorrente' WHERE id = 1"
                )
                await conn2.commit()
            except aiosqlite.OperationalError as exc:
                pytest.fail(
                    "Escrita concorrente bloqueada enquanto o Haiku estava em voo "
                    f"({exc}) — a transação do funil segura o write lock através do await de rede"
                )

            row = await conn2.execute(
                "SELECT funnel_product FROM conversations WHERE id = 1"
            )
            conv = await row.fetchone()
            assert conv["funnel_product"] == "curso-cdo", (
                "Funil ainda não commitado quando o Haiku foi chamado: segunda conexão "
                f"enxerga funnel_product={conv['funnel_product']!r} em vez de 'curso-cdo'"
            )
        finally:
            # Teardown: libera o mock e aguarda a task pra não vazar conexão/thread
            libera_llm.set()
            if task is not None:
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(task, timeout=10)
            if conn2 is not None:
                await conn2.close()


@pytest.mark.asyncio
async def test_carga_escritas_concorrentes_durante_llm(file_db_path):
    """20 escritas curtas concorrentes durante a geração: zero 'database is locked'
    e p95 de latência abaixo de 500ms."""
    entrou_no_llm = asyncio.Event()

    async def haiku_lento(*args, **kwargs):
        entrou_no_llm.set()
        await asyncio.sleep(1.5)  # simula a latência de rede das chamadas Haiku
        return ("rascunho de teste", "justificativa de teste", None)

    mock_haiku = AsyncMock(side_effect=haiku_lento)

    async def escrita_curta(i: int) -> float:
        """INSERT curto por conexão nova independente; retorna a latência em segundos."""
        inicio = time.perf_counter()
        conn = await aiosqlite.connect(str(file_db_path))
        try:
            await conn.execute("PRAGMA busy_timeout = 2000")
            await conn.execute(
                "INSERT INTO messages (conversation_id, evolution_message_id, direction, content) "
                "VALUES (1, ?, 'inbound', 'escrita concorrente')",
                (f"conc-{i}",),
            )
            await conn.commit()
        finally:
            await conn.close()
        return time.perf_counter() - inicio

    task = None
    with _patches_draft_engine(file_db_path, mock_haiku):
        try:
            task = asyncio.create_task(generate_drafts(1, 1))
            await asyncio.wait_for(entrou_no_llm.wait(), timeout=10)

            resultados = await asyncio.gather(
                *(escrita_curta(i) for i in range(20)), return_exceptions=True
            )
        finally:
            if task is not None:
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(task, timeout=15)

    erros = [r for r in resultados if isinstance(r, BaseException)]
    assert not erros, (
        f"{len(erros)}/20 escritas concorrentes falharam durante a geração "
        f"(primeira: {erros[0]!r}) — write lock seguro através do await de rede"
    )

    latencias = sorted(r for r in resultados if not isinstance(r, BaseException))
    p95 = latencias[int(0.95 * (len(latencias) - 1))]
    assert p95 < 0.5, (
        f"p95 de latência de escrita concorrente = {p95 * 1000:.0f}ms (limite 500ms) — "
        "escritores esperam a transação do funil que atravessa as chamadas LLM"
    )
