import pytest

from app.services.cold_triage import apply_matrix


# cap não atingido, confidence high. Matriz agora é classification × stage_reached.
@pytest.mark.parametrize(
    "classification,stage,expected",
    [
        # link_sent
        ("objecao_preco", "link_sent", "mentoria"),
        ("objecao_timing", "link_sent", "mentoria"),
        ("objecao_conteudo", "link_sent", "mentoria"),
        ("tire_kicker", "link_sent", "skip"),
        ("negativo_explicito", "link_sent", "skip"),
        ("perdido_no_ruido", "link_sent", "conteudo"),
        ("nao_classificavel", "link_sent", "skip"),
        # handbook_sent
        ("objecao_preco", "handbook_sent", "skip"),
        ("objecao_timing", "handbook_sent", "mentoria"),
        ("objecao_conteudo", "handbook_sent", "conteudo"),
        ("tire_kicker", "handbook_sent", "skip"),
        ("negativo_explicito", "handbook_sent", "skip"),
        ("perdido_no_ruido", "handbook_sent", "skip"),
        # only_qualifying
        ("objecao_preco", "only_qualifying", "skip"),
        ("objecao_timing", "only_qualifying", "conteudo"),
        ("objecao_conteudo", "only_qualifying", "conteudo"),
        ("tire_kicker", "only_qualifying", "skip"),
        ("negativo_explicito", "only_qualifying", "skip"),
        ("perdido_no_ruido", "only_qualifying", "skip"),
        # nunca_qualificou
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
        ("objecao_preco", "link_sent", "conteudo"),
        ("objecao_timing", "link_sent", "conteudo"),
        ("objecao_conteudo", "link_sent", "conteudo"),
        ("objecao_timing", "handbook_sent", "conteudo"),
        ("objecao_conteudo", "handbook_sent", "conteudo"),  # já era conteudo, mantém
        # only_qualifying/nunca_qualificou nunca foram mentoria, não mudam com cap
        ("objecao_timing", "only_qualifying", "conteudo"),
        ("objecao_timing", "nunca_qualificou", "skip"),
    ],
)
def test_matrix_cap_reached(classification, stage, expected):
    assert apply_matrix(classification, stage, mentoria_used=15, cap=15, confidence="high") == expected


def test_low_confidence_always_skip():
    assert apply_matrix("objecao_timing", "link_sent", mentoria_used=0, cap=15, confidence="low") == "skip"
    assert apply_matrix("perdido_no_ruido", "link_sent", mentoria_used=0, cap=15, confidence="low") == "skip"
    assert apply_matrix("objecao_preco", "handbook_sent", mentoria_used=0, cap=15, confidence="low") == "skip"


def test_medium_confidence_respects_matrix():
    assert apply_matrix("objecao_timing", "link_sent", mentoria_used=0, cap=15, confidence="med") == "mentoria"
    assert apply_matrix("objecao_timing", "only_qualifying", mentoria_used=0, cap=15, confidence="med") == "conteudo"


def test_unknown_stage_defaults_to_skip():
    assert apply_matrix("objecao_timing", "unknown_stage", mentoria_used=0, cap=15, confidence="high") == "skip"
