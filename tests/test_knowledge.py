import os
import tempfile
import time

import pytest

from app.services import knowledge


@pytest.fixture
def temp_knowledge_dir(tmp_path):
    """Temporary knowledge directory."""
    original_dir = knowledge.KNOWLEDGE_DIR
    knowledge.KNOWLEDGE_DIR = tmp_path
    knowledge._cache = None
    knowledge._cache_mtime = {}
    yield tmp_path
    knowledge.KNOWLEDGE_DIR = original_dir
    knowledge._cache = None
    knowledge._cache_mtime = {}


def test_load_knowledge_files(temp_knowledge_dir):
    """15.1: loader carrega todos os .md e retorna conteúdo concatenado."""
    (temp_knowledge_dir / "curso-a.md").write_text("Curso A content")
    (temp_knowledge_dir / "curso-b.md").write_text("Curso B content")

    result = knowledge.load_knowledge_base()
    assert "Curso A content" in result
    assert "Curso B content" in result


def test_empty_directory(temp_knowledge_dir):
    """15.2: diretório vazio retorna string vazia."""
    result = knowledge.load_knowledge_base()
    assert result == ""


def test_reload_on_modification(temp_knowledge_dir):
    """15.3: arquivo modificado é recarregado."""
    f = temp_knowledge_dir / "test.md"
    f.write_text("version 1")

    result1 = knowledge.load_knowledge_base()
    assert "version 1" in result1

    # Ensure mtime changes
    time.sleep(0.1)
    f.write_text("version 2")

    result2 = knowledge.load_knowledge_base()
    assert "version 2" in result2
