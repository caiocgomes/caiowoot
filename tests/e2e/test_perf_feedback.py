"""Testes RED (TDD) de feedback de performance no frontend.

Contrato novo (ainda não implementado):
- Regenerate dá feedback imediato (.draft-loading + botões desabilitados).
- Clique repetido no regenerate dispara apenas 1 POST (guard).
- Polling de GET /conversations/{id} morre após o clique (fluxo passa a ser WS).
- Erro no regenerate mostra toast de erro, reabilita botões e preserva os cards.
- Erro no classify reabilita o botão (bug conhecido: trava para sempre).
- Rajada de new_message via webhook gera no máximo 2 GETs na lista (debounce).

Todos devem falhar HOJE por assert de comportamento, com timeouts curtos.
"""

import json
import os
import sqlite3
import uuid

import requests
from playwright.sync_api import expect

REGEN_OK_BODY = json.dumps({"status": "ok"})


def _open_conversation(page, live_server):
    """Navega e abre a conversa 1 (Mabel), aguardando os drafts."""
    page.goto(live_server)
    page.wait_for_selector(".conv-item", timeout=5000)
    # Seleciona pela âncora do nome para não depender da ordenação da lista
    page.locator(".conv-item", has_text="Mabel").first.click()
    page.wait_for_selector("#messages", timeout=5000)
    page.wait_for_selector(".draft-card", timeout=5000)


def _fulfill_regen_ok(route):
    """Responde o POST de regenerate com sucesso sintético."""
    route.fulfill(status=200, content_type="application/json", body=REGEN_OK_BODY)


def test_regenerate_shows_immediate_feedback(live_server, desktop_page):
    """Ao clicar em regenerar, .draft-loading aparece em até 2s e os botões de
    regeneração ficam desabilitados enquanto a requisição está em voo."""
    desktop_page.route("**/conversations/1/regenerate", _fulfill_regen_ok)

    _open_conversation(desktop_page, live_server)

    desktop_page.locator("#instruction-input").fill("foca no preço")
    desktop_page.locator("#regen-instruction-btn").click()

    # Feedback imediato: indicador de loading visível
    expect(desktop_page.locator(".draft-loading")).to_be_visible(timeout=2000)

    # Botões de regeneração desabilitados enquanto gera
    expect(desktop_page.locator("#regen-instruction-btn")).to_be_disabled(timeout=2000)
    expect(desktop_page.locator("#regen-all-btn")).to_be_disabled(timeout=2000)


def test_regenerate_repeated_clicks_single_post(live_server, desktop_page):
    """Três cliques rápidos no botão de regenerar devem disparar exatamente
    1 POST /regenerate (guard contra clique repetido)."""
    post_count = {"n": 0}

    def count_and_fulfill(route):
        if route.request.method == "POST":
            post_count["n"] += 1
        _fulfill_regen_ok(route)

    desktop_page.route("**/conversations/1/regenerate", count_and_fulfill)

    _open_conversation(desktop_page, live_server)

    desktop_page.locator("#instruction-input").fill("foca no preço")
    btn = desktop_page.locator("#regen-instruction-btn")
    # force=True: no contrato novo o botão fica desabilitado após o 1º clique;
    # cliques forçados em botão desabilitado não disparam o handler (semântica
    # nativa do browser), então o teste segue válido na fase GREEN.
    btn.click(force=True)
    btn.click(force=True)
    btn.click(force=True)

    # Dá 1s de chance para POSTs extras chegarem
    desktop_page.wait_for_timeout(1000)

    assert post_count["n"] == 1, (
        f"Esperava exatamente 1 POST /regenerate com 3 cliques rápidos "
        f"(guard de clique repetido), ocorreram {post_count['n']}"
    )


def test_regenerate_no_polling_after_click(live_server, desktop_page):
    """Após clicar em regenerar, nenhum GET /conversations/1 de polling deve
    ser disparado — a atualização passa a chegar via WebSocket."""
    get_count = {"n": 0}

    def count_conv_detail(route):
        if route.request.method == "GET":
            get_count["n"] += 1
        route.continue_()

    desktop_page.route("**/conversations/1", count_conv_detail)
    desktop_page.route("**/conversations/1/regenerate", _fulfill_regen_ok)

    _open_conversation(desktop_page, live_server)

    desktop_page.locator("#instruction-input").fill("foca no preço")
    desktop_page.locator("#regen-instruction-btn").click()

    # Zera o contador: os GETs do load inicial não contam, só os pós-clique
    get_count["n"] = 0
    desktop_page.wait_for_timeout(4000)

    assert get_count["n"] == 0, (
        f"Esperava zero GETs /conversations/1 após o clique (polling morto, "
        f"update via WS), ocorreram {get_count['n']} em 4s"
    )


def test_regenerate_error_shows_toast_and_reenables(live_server, desktop_page):
    """Se o POST /regenerate falha (500), o operador vê toast de erro em até
    2s, os botões voltam a ficar habilitados e os 3 cards antigos permanecem."""
    desktop_page.route(
        "**/conversations/1/regenerate",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps({"detail": "erro interno"}),
        ),
    )

    _open_conversation(desktop_page, live_server)

    desktop_page.locator("#instruction-input").fill("foca no preço")
    desktop_page.locator("#regen-instruction-btn").click()

    # Toast de erro visível (classe .toast-error, ver app/static/js/ui/toast.js)
    expect(desktop_page.locator(".toast-error")).to_be_visible(timeout=2000)

    # Botões reabilitados após o erro
    expect(desktop_page.locator("#regen-instruction-btn")).to_be_enabled(timeout=2000)
    expect(desktop_page.locator("#regen-all-btn")).to_be_enabled(timeout=2000)

    # Os 3 cards antigos continuam na tela (nada foi descartado)
    assert desktop_page.locator(".draft-card").count() == 3, (
        f"Esperava os 3 draft cards preservados após erro de regenerate, "
        f"encontrei {desktop_page.locator('.draft-card').count()}"
    )


def test_classify_reenables_button_on_error(live_server, desktop_page):
    """Se o POST /classify falha (500), o botão #ctx-classify-btn deve voltar
    a ficar habilitado em até 3s e um toast de erro deve aparecer.

    Bug conhecido: hoje o botão trava desabilitado para sempre
    (app/static/js/ui/context-panel.js:33-58, caminho de erro não reabilita)."""
    desktop_page.route(
        "**/conversations/1/classify",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps({"detail": "erro interno"}),
        ),
    )

    _open_conversation(desktop_page, live_server)

    btn = desktop_page.locator("#ctx-classify-btn")
    btn.click()

    # Botão destrava após o erro
    expect(btn).to_be_enabled(timeout=3000)

    # E o erro é comunicado via toast
    expect(desktop_page.locator(".toast-error")).to_be_visible(timeout=2000)


def _make_webhook_payload(phone, text, message_id, push_name="Lead Novo"):
    """Payload no formato Evolution API (espelha make_webhook_payload de
    tests/conftest.py)."""
    return {
        "event": "messages.upsert",
        "instance": {"instanceName": "test-instance"},
        "data": {
            "key": {
                "remoteJid": f"{phone}@s.whatsapp.net",
                "fromMe": False,
                "id": message_id,
            },
            "pushName": push_name,
            "messageType": "conversation",
            "message": {"conversation": text},
        },
    }


def _delete_conversation_by_phone(phone):
    """Remove do DB seedado a conversa criada pelo teste de rajada, para não
    alterar a ordenação da lista vista pelos demais testes e2e da sessão."""
    db_path = os.environ.get("DATABASE_PATH")
    if not db_path:
        return
    conn = sqlite3.connect(db_path, timeout=5)
    try:
        row = conn.execute(
            "SELECT id FROM conversations WHERE phone_number = ?", (phone,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (row[0],))
            conn.execute("DELETE FROM conversations WHERE id = ?", (row[0],))
            conn.commit()
    finally:
        conn.close()


def test_conversation_list_debounced_on_message_burst(live_server, desktop_page):
    """Rajada de 5 webhooks (mensagens de OUTRO telefone) deve gerar no máximo
    2 GETs /conversations (lista) em 3s — hoje é 1 GET por evento new_message."""
    burst_phone = "5511888888888"
    list_count = {"n": 0}

    def count_list(route):
        if route.request.method == "GET":
            list_count["n"] += 1
        route.continue_()

    # Padrão casa só com a lista (URL termina em /conversations, sem id)
    desktop_page.route("**/conversations", count_list)

    _open_conversation(desktop_page, live_server)

    # Garante WebSocket conectado antes da rajada (broadcast chega no browser)
    desktop_page.wait_for_selector(".ws-dot.connected", timeout=5000)

    try:
        # Zera o contador: só interessam os GETs disparados pela rajada
        list_count["n"] = 0

        run_id = uuid.uuid4().hex[:8]
        for i in range(5):
            payload = _make_webhook_payload(
                phone=burst_phone,
                text=f"Mensagem de rajada {i}",
                message_id=f"perf-burst-{run_id}-{i}",
            )
            r = requests.post(f"{live_server}/webhook", json=payload, timeout=5)
            assert r.status_code == 200, f"webhook falhou: {r.status_code} {r.text}"

        # Janela de observação: eventos new_message chegam via WS e disparam
        # (hoje) um loadConversations cada
        desktop_page.wait_for_timeout(3000)

        assert list_count["n"] <= 2, (
            f"Esperava no máximo 2 GETs /conversations em 3s com debounce, "
            f"ocorreram {list_count['n']} para 5 eventos new_message"
        )
    finally:
        _delete_conversation_by_phone(burst_phone)
