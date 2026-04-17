import pytest

from app.services.cold_triage import apply_matrix


# cap não atingido, confidence high. Matriz agora é classification × stage_reached.
@pytest.mark.parametrize(
    "classification,stage,expected",
    [
        # link_sent: quase tudo vira mentoria; só negativo_explicito skipa
        ("abandono_checkout", "link_sent", "mentoria"),
        ("objecao_preco", "link_sent", "mentoria"),
        ("objecao_timing", "link_sent", "mentoria"),
        ("objecao_conteudo", "link_sent", "mentoria"),
        ("tire_kicker", "link_sent", "mentoria"),          # fallback: Haiku errou classificação
        ("negativo_explicito", "link_sent", "skip"),       # única exceção: hostilidade
        ("perdido_no_ruido", "link_sent", "mentoria"),     # era conteudo, agora mentoria
        ("nao_classificavel", "link_sent", "mentoria"),    # rede de segurança
        # handbook_sent
        ("abandono_checkout", "handbook_sent", "mentoria"),
        ("objecao_preco", "handbook_sent", "skip"),
        ("objecao_timing", "handbook_sent", "mentoria"),
        ("objecao_conteudo", "handbook_sent", "conteudo"),
        ("tire_kicker", "handbook_sent", "skip"),
        ("negativo_explicito", "handbook_sent", "skip"),
        ("perdido_no_ruido", "handbook_sent", "skip"),
        # only_qualifying
        ("abandono_checkout", "only_qualifying", "conteudo"),
        ("objecao_preco", "only_qualifying", "skip"),
        ("objecao_timing", "only_qualifying", "conteudo"),
        ("objecao_conteudo", "only_qualifying", "conteudo"),
        ("tire_kicker", "only_qualifying", "skip"),
        ("negativo_explicito", "only_qualifying", "skip"),
        ("perdido_no_ruido", "only_qualifying", "skip"),
        # nunca_qualificou: tudo skip
        ("abandono_checkout", "nunca_qualificou", "skip"),
        ("objecao_preco", "nunca_qualificou", "skip"),
        ("objecao_timing", "nunca_qualificou", "skip"),
        ("objecao_conteudo", "nunca_qualificou", "skip"),
        ("tire_kicker", "nunca_qualificou", "skip"),
        ("negativo_explicito", "nunca_qualificou", "skip"),
        ("perdido_no_ruido", "nunca_qualificou", "skip"),
        ("nao_classificavel", "nunca_qualificou", "skip"),
    ],
)
def test_matrix_cap_not_reached(classification, stage, expected):
    assert apply_matrix(classification, stage, mentoria_used=0, cap=15, confidence="high") == expected


# cap atingido: mentoria rebaixa conforme _DEMOTE_WHEN_CAP
@pytest.mark.parametrize(
    "classification,stage,expected",
    [
        # Todas as combinações que viram mentoria em link_sent viram conteudo com cap
        ("abandono_checkout", "link_sent", "conteudo"),
        ("objecao_preco", "link_sent", "conteudo"),
        ("objecao_timing", "link_sent", "conteudo"),
        ("objecao_conteudo", "link_sent", "conteudo"),
        ("tire_kicker", "link_sent", "conteudo"),
        ("perdido_no_ruido", "link_sent", "conteudo"),
        ("nao_classificavel", "link_sent", "conteudo"),
        # handbook_sent: mentoria vira conteudo
        ("objecao_timing", "handbook_sent", "conteudo"),
        ("objecao_conteudo", "handbook_sent", "conteudo"),
        ("abandono_checkout", "handbook_sent", "conteudo"),
        # only_qualifying: já era conteudo, mantém
        ("objecao_timing", "only_qualifying", "conteudo"),
        ("objecao_timing", "nunca_qualificou", "skip"),
    ],
)
def test_matrix_cap_reached(classification, stage, expected):
    assert apply_matrix(classification, stage, mentoria_used=15, cap=15, confidence="high") == expected


def test_abandono_checkout_is_highest_priority_score():
    """O padrão 'pediu link, sumiu' deve ter prioridade máxima no score."""
    from app.services.cold_triage import score_candidate
    abandono = score_candidate("abandono_checkout", "link_sent", 40.0, "me manda o link")
    objecao_timing = score_candidate("objecao_timing", "link_sent", 40.0, "mes que vem volto")
    objecao_preco = score_candidate("objecao_preco", "link_sent", 40.0, "caro")
    perdido = score_candidate("perdido_no_ruido", "link_sent", 40.0, "")
    assert abandono > objecao_timing
    assert abandono > objecao_preco
    assert abandono > perdido


def test_low_confidence_on_strong_stage_falls_back_to_perdido_no_ruido():
    """Low confidence em link/handbook NÃO força skip: vira perdido_no_ruido e segue matriz.
    Rationale: quem chegou no funil de venda é valioso demais pra descartar por dúvida."""
    # link_sent + low → perdido_no_ruido × link_sent = mentoria
    assert apply_matrix("nao_classificavel", "link_sent", mentoria_used=0, cap=15, confidence="low") == "mentoria"
    assert apply_matrix("objecao_timing", "link_sent", mentoria_used=0, cap=15, confidence="low") == "mentoria"
    # handbook_sent + low → perdido_no_ruido × handbook_sent = skip (matriz diz skip)
    assert apply_matrix("objecao_preco", "handbook_sent", mentoria_used=0, cap=15, confidence="low") == "skip"


def test_low_confidence_on_weak_stage_still_skips():
    """Low confidence em only_qualifying ou nunca_qualificou continua forçando skip."""
    assert apply_matrix("objecao_timing", "only_qualifying", mentoria_used=0, cap=15, confidence="low") == "skip"
    assert apply_matrix("objecao_timing", "nunca_qualificou", mentoria_used=0, cap=15, confidence="low") == "skip"


def test_medium_confidence_respects_matrix():
    assert apply_matrix("objecao_timing", "link_sent", mentoria_used=0, cap=15, confidence="med") == "mentoria"
    assert apply_matrix("objecao_timing", "only_qualifying", mentoria_used=0, cap=15, confidence="med") == "conteudo"
    assert apply_matrix("abandono_checkout", "link_sent", mentoria_used=0, cap=15, confidence="med") == "mentoria"


def test_unknown_stage_defaults_to_skip():
    assert apply_matrix("objecao_timing", "unknown_stage", mentoria_used=0, cap=15, confidence="high") == "skip"


def test_negativo_explicito_always_skip_even_at_link():
    """Hostilidade nunca vira toque, mesmo em link_sent (regra inviolável)."""
    assert apply_matrix("negativo_explicito", "link_sent", mentoria_used=0, cap=15, confidence="high") == "skip"
    assert apply_matrix("negativo_explicito", "handbook_sent", mentoria_used=0, cap=15, confidence="high") == "skip"


def test_ja_comprou_always_skip_regardless_of_stage_or_confidence():
    """Lead que já comprou nunca vira toque. Regra zero."""
    for stage in ("link_sent", "handbook_sent", "only_qualifying", "nunca_qualificou"):
        for conf in ("high", "med", "low"):
            assert apply_matrix("ja_comprou", stage, mentoria_used=0, cap=15, confidence=conf) == "skip"


def test_ja_comprou_skip_not_overridden_by_cap():
    """Cap atingido não transforma ja_comprou em conteudo. Skip sempre."""
    assert apply_matrix("ja_comprou", "link_sent", mentoria_used=99, cap=15, confidence="high") == "skip"
