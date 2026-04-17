import pytest

from app.services.cold_triage import apply_matrix


# cap não atingido, confidence high
@pytest.mark.parametrize(
    "classification,stage,expected",
    [
        ("objecao_preco", "link_sent", "mentoria"),
        ("objecao_preco", "handbook_sent", "skip"),
        ("objecao_timing", "link_sent", "mentoria"),
        ("objecao_timing", "handbook_sent", "mentoria"),
        ("objecao_conteudo", "link_sent", "mentoria"),
        ("objecao_conteudo", "handbook_sent", "conteudo"),
        ("tire_kicker", "link_sent", "skip"),
        ("tire_kicker", "handbook_sent", "skip"),
        ("negativo_explicito", "link_sent", "skip"),
        ("negativo_explicito", "handbook_sent", "skip"),
        ("perdido_no_ruido", "link_sent", "conteudo"),
        ("perdido_no_ruido", "handbook_sent", "skip"),
        ("nao_classificavel", "link_sent", "skip"),
        ("nao_classificavel", "handbook_sent", "skip"),
    ],
)
def test_matrix_cap_not_reached(classification, stage, expected):
    assert apply_matrix(classification, stage, mentoria_used=0, cap=15, confidence="high") == expected


# cap atingido: mentoria vira conteudo (link) ou skip (handbook)
@pytest.mark.parametrize(
    "classification,stage,expected",
    [
        ("objecao_preco", "link_sent", "conteudo"),
        ("objecao_preco", "handbook_sent", "skip"),
        ("objecao_timing", "link_sent", "conteudo"),
        ("objecao_timing", "handbook_sent", "skip"),
        ("objecao_conteudo", "link_sent", "conteudo"),
        ("objecao_conteudo", "handbook_sent", "conteudo"),
        ("perdido_no_ruido", "link_sent", "conteudo"),
    ],
)
def test_matrix_cap_reached(classification, stage, expected):
    assert apply_matrix(classification, stage, mentoria_used=15, cap=15, confidence="high") == expected


def test_low_confidence_always_skip():
    # Mesmo classification=objecao_timing + link_sent deveria ser mentoria, mas low → skip
    assert apply_matrix("objecao_timing", "link_sent", mentoria_used=0, cap=15, confidence="low") == "skip"
    assert apply_matrix("perdido_no_ruido", "link_sent", mentoria_used=0, cap=15, confidence="low") == "skip"


def test_medium_confidence_respects_matrix():
    # Med confidence não rebaixa
    assert apply_matrix("objecao_timing", "link_sent", mentoria_used=0, cap=15, confidence="med") == "mentoria"
