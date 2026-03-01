import os
import tempfile
import pytest
from unittest.mock import patch, AsyncMock

import chromadb

os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_INSTANCE", "test-instance")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from app.services.smart_retrieval import index_edit_pair, retrieve_similar, update_metadata


@pytest.fixture
def chroma_collection():
    client = chromadb.Client()
    # Delete if exists from previous test
    try:
        client.delete_collection("test_situations")
    except Exception:
        pass
    collection = client.create_collection(
        name="test_situations",
        metadata={"hnsw:space": "cosine"},
    )
    with patch("app.services.smart_retrieval.get_chroma_collection", return_value=collection):
        yield collection
    try:
        client.delete_collection("test_situations")
    except Exception:
        pass


def test_index_and_retrieve(chroma_collection):
    index_edit_pair(1, "Primeiro contato, cliente perguntou preço sem qualificação.", was_edited=True)
    index_edit_pair(2, "Cliente já qualificado, objeção de preço ativa.", was_edited=True)
    index_edit_pair(3, "Conversa sobre conteúdo do curso CDO, cliente técnico.", was_edited=False)

    results = retrieve_similar("Cliente novo perguntando quanto custa", k=2)
    assert len(results) == 2
    assert all(isinstance(r, int) for r in results)


def test_retrieve_empty_collection(chroma_collection):
    results = retrieve_similar("Qualquer coisa", k=5)
    assert results == []


def test_validated_pairs_prioritized(chroma_collection):
    index_edit_pair(1, "Primeiro contato genérico.", validated=False)
    index_edit_pair(2, "Primeiro contato genérico.", validated=True)
    index_edit_pair(3, "Primeiro contato genérico.", validated=True)

    results = retrieve_similar("Primeiro contato", k=2)
    # Validated pairs should come first
    assert 2 in results or 3 in results


def test_rejected_pairs_excluded(chroma_collection):
    index_edit_pair(1, "Objeção de preço simples.", validated=True, rejected=False)
    index_edit_pair(2, "Objeção de preço simples.", validated=True, rejected=True)

    results = retrieve_similar("Objeção de preço", k=5)
    assert 1 in results
    assert 2 not in results


def test_cold_start_returns_all_available(chroma_collection):
    index_edit_pair(1, "Único par disponível.")
    results = retrieve_similar("Algo similar", k=5)
    assert len(results) == 1
    assert results[0] == 1


def test_update_metadata(chroma_collection):
    index_edit_pair(1, "Teste de update.", validated=False)
    update_metadata(1, validated=True)
    existing = chroma_collection.get(ids=["1"])
    assert existing["metadatas"][0]["validated"] is True


def test_fills_from_non_validated_when_insufficient(chroma_collection):
    index_edit_pair(1, "Contato sobre curso.", validated=True)
    index_edit_pair(2, "Contato sobre curso parecido.", validated=False)
    index_edit_pair(3, "Contato sobre outro curso.", validated=False)

    results = retrieve_similar("Curso de IA", k=3)
    assert len(results) == 3
