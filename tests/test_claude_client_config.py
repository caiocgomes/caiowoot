"""Configuração explícita do cliente Anthropic (timeout e max_retries).

Contrato (fase GREEN): get_anthropic_client cria o AsyncAnthropic com
timeout=30.0 e max_retries=2, em vez dos defaults do SDK (timeout de 600s).
Timeout curto evita que drafts fiquem pendurados atrás de chamadas travadas.

Hoje: red — o cliente é criado só com api_key, herdando os defaults do SDK.
"""

import app.services.claude_client as claude_client


def test_get_anthropic_client_configura_timeout_e_max_retries(monkeypatch):
    """get_anthropic_client deve criar o cliente com timeout=30.0 e max_retries=2."""
    # Reseta o singleton pra forçar criação de um cliente novo;
    # o monkeypatch restaura o valor original no teardown.
    monkeypatch.setattr(claude_client, "_client", None)

    client = claude_client.get_anthropic_client()

    assert client.timeout == 30.0, (
        f"timeout esperado 30.0, veio {client.timeout!r} (default do SDK)"
    )
    assert client.max_retries == 2, (
        f"max_retries esperado 2, veio {client.max_retries!r}"
    )
