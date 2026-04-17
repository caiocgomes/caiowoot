"""Testes da proteção contra disparo para leads que já compraram."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import *  # noqa: F401, F403

from app.services.cold_triage import (
    COLD_CLASSIFY_TOOL_NAME,
    COLD_COMPOSE_TOOL_NAME,
    run_preview,
)


def _classify_resp(classification, confidence="high", stage_reached="link_sent", quote="paguei aqui", reasoning="x"):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": classification,
        "confidence": confidence,
        "stage_reached": stage_reached,
        "quote_from_lead": quote,
        "reasoning": reasoning,
    }
    mock.content = [block]
    return mock


def _compose_resp(message):
    mock = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_COMPOSE_TOOL_NAME
    block.input = {"message": message}
    mock.content = [block]
    return mock


async def _seed_cold_conv(db, phone):
    cursor = await db.execute(
        "INSERT INTO conversations (phone_number, contact_name, funnel_product, funnel_stage) "
        "VALUES (?, 'Ana', 'curso-cdo', 'qualifying')",
        (phone,),
    )
    conv_id = cursor.lastrowid
    await db.execute(
        "INSERT INTO messages (conversation_id, direction, content, created_at) "
        "VALUES (?, 'inbound', 'paguei aqui e ja acessei a plataforma', datetime('now','-40 days'))",
        (conv_id,),
    )
    await db.commit()
    return conv_id


@pytest.mark.asyncio
async def test_ja_comprou_lead_marked_do_not_contact(db):
    """Lead classificado como ja_comprou: skip + cold_do_not_contact=1 na conversa."""
    conv_id = await _seed_cold_conv(db, "5511")

    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("ja_comprou", "high", "link_sent", "paguei aqui")
        return _compose_resp("nao usado")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        items = await run_preview(db=db)

    # Aparece no preview com action=skip
    assert len(items) == 1
    assert items[0]["action"] == "skip"
    assert items[0]["classification"] == "ja_comprou"

    # cold_do_not_contact foi marcado na conversa
    cur = await db.execute(
        "SELECT cold_do_not_contact FROM conversations WHERE id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["cold_do_not_contact"] == 1


@pytest.mark.asyncio
async def test_ja_comprou_lead_never_returns_to_pool_after_marked(db):
    """Depois de marcado do-not-contact, o lead sai do pool de candidatos."""
    conv_id = await _seed_cold_conv(db, "5522")

    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("ja_comprou", "high", "link_sent", "paguei")
        return _compose_resp("nao usado")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        await run_preview(db=db)

    # Segundo preview: não inclui o lead
    from app.services.cold_triage import select_cold_candidates
    candidates = await select_cold_candidates(db)
    assert not any(c["id"] == conv_id for c in candidates)


@pytest.mark.asyncio
async def test_non_purchase_leads_not_marked_do_not_contact(db):
    """Lead classificado como objecao_preco não dispara cold_do_not_contact."""
    conv_id = await _seed_cold_conv(db, "5533")

    mock_client = AsyncMock()

    def dispatcher(*args, **kwargs):
        tools = kwargs.get("tools") or []
        tool_name = tools[0]["name"] if tools else ""
        if tool_name == COLD_CLASSIFY_TOOL_NAME:
            return _classify_resp("objecao_preco", "high", "link_sent", "ta salgado")
        return _compose_resp("oi")

    mock_client.messages.create = AsyncMock(side_effect=dispatcher)

    with patch("app.services.cold_triage.get_anthropic_client", return_value=mock_client):
        await run_preview(db=db)

    cur = await db.execute(
        "SELECT cold_do_not_contact FROM conversations WHERE id = ?",
        (conv_id,),
    )
    row = await cur.fetchone()
    assert row["cold_do_not_contact"] == 0


# ─────────── Guarda contra falso-positivo de ja_comprou ───────────

from app.services.cold_triage import (
    _has_purchase_evidence,
    _parse_classify_response,
)


def test_has_purchase_evidence_detects_past_tense():
    """Padrões retrospectivos reais são detectados."""
    assert _has_purchase_evidence("paguei aqui e já acessei a plataforma")
    assert _has_purchase_evidence("comprei ontem")
    assert _has_purchase_evidence("fechei a compra pelo cartao")
    assert _has_purchase_evidence("cartão passou, obrigado")
    assert _has_purchase_evidence("recebi o email de acesso")
    assert _has_purchase_evidence("fiz a inscrição agora")
    assert _has_purchase_evidence("me inscrevi")
    assert _has_purchase_evidence("chegou o acesso")
    assert _has_purchase_evidence("ja to dentro", "")
    assert _has_purchase_evidence("entrei no curso")


def test_has_purchase_evidence_ignores_intent():
    """Intenção NÃO é confundida com confirmação."""
    assert not _has_purchase_evidence("combinado")
    assert not _has_purchase_evidence("fechado, vou pagar")
    assert not _has_purchase_evidence("vou comprar amanhã")
    assert not _has_purchase_evidence("quero comprar")
    assert not _has_purchase_evidence("beleza")
    assert not _has_purchase_evidence("ok, me manda")
    assert not _has_purchase_evidence("")
    assert not _has_purchase_evidence("valeu, depois a gente fala")


def test_parse_classify_rebaixa_ja_comprou_sem_evidencia():
    """Caso Diogo: Haiku diz ja_comprou mas quote é 'Combinado'. Deve virar abandono_checkout."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": "ja_comprou",
        "confidence": "high",
        "stage_reached": "link_sent",
        "quote_from_lead": "Combinado",
        "reasoning": "Lead confirmou intencao de compra apos receber link",
    }
    resp = MagicMock()
    resp.content = [block]

    result = _parse_classify_response(resp)
    assert result["classification"] == "abandono_checkout"
    assert result["quote_from_lead"] == "Combinado"


def test_parse_classify_mantem_ja_comprou_com_evidencia():
    """Haiku marca ja_comprou e quote tem 'paguei'. Mantém ja_comprou."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": "ja_comprou",
        "confidence": "high",
        "stage_reached": "link_sent",
        "quote_from_lead": "Paguei aqui e ja acessei a plataforma",
        "reasoning": "Lead confirmou pagamento e acesso",
    }
    resp = MagicMock()
    resp.content = [block]

    result = _parse_classify_response(resp)
    assert result["classification"] == "ja_comprou"


def test_parse_classify_rebaixa_ja_comprou_com_evidencia_no_reasoning():
    """Evidência retrospectiva pode estar no reasoning, não necessariamente no quote."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = COLD_CLASSIFY_TOOL_NAME
    block.input = {
        "classification": "ja_comprou",
        "confidence": "high",
        "stage_reached": "link_sent",
        "quote_from_lead": "obrigado",
        "reasoning": "Lead escreveu que recebeu o acesso e entrou no curso",
    }
    resp = MagicMock()
    resp.content = [block]

    result = _parse_classify_response(resp)
    assert result["classification"] == "ja_comprou"
