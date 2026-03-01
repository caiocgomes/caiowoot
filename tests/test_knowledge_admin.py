import pytest
import pytest_asyncio
from pathlib import Path

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.routes import knowledge as knowledge_routes


@pytest.fixture
def temp_knowledge_dir(tmp_path):
    """Swap KNOWLEDGE_DIR to a temp directory."""
    original = knowledge_routes.KNOWLEDGE_DIR
    knowledge_routes.KNOWLEDGE_DIR = tmp_path
    yield tmp_path
    knowledge_routes.KNOWLEDGE_DIR = original


@pytest_asyncio.fixture
async def client(temp_knowledge_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
class TestListDocs:
    async def test_list_empty(self, client, temp_knowledge_dir):
        res = await client.get("/knowledge")
        assert res.status_code == 200
        assert res.json() == []

    async def test_list_with_docs(self, client, temp_knowledge_dir):
        (temp_knowledge_dir / "curso-cdo.md").write_text("content")
        (temp_knowledge_dir / "playbook.md").write_text("content")
        res = await client.get("/knowledge")
        assert res.status_code == 200
        names = [d["name"] for d in res.json()]
        assert "curso-cdo" in names
        assert "playbook" in names


@pytest.mark.asyncio
class TestGetDoc:
    async def test_get_existing(self, client, temp_knowledge_dir):
        (temp_knowledge_dir / "curso-cdo.md").write_text("# CDO content")
        res = await client.get("/knowledge/curso-cdo")
        assert res.status_code == 200
        assert res.json()["content"] == "# CDO content"

    async def test_get_not_found(self, client):
        res = await client.get("/knowledge/nao-existe")
        assert res.status_code == 404


@pytest.mark.asyncio
class TestCreateDoc:
    async def test_create_success(self, client, temp_knowledge_dir):
        res = await client.post("/knowledge", json={"name": "faq-precos", "content": "# FAQ"})
        assert res.status_code == 201
        assert (temp_knowledge_dir / "faq-precos.md").read_text() == "# FAQ"

    async def test_create_conflict(self, client, temp_knowledge_dir):
        (temp_knowledge_dir / "curso-cdo.md").write_text("existing")
        res = await client.post("/knowledge", json={"name": "curso-cdo", "content": "new"})
        assert res.status_code == 409

    async def test_create_invalid_name(self, client):
        res = await client.post("/knowledge", json={"name": "../.env", "content": "hack"})
        assert res.status_code == 422

    async def test_create_invalid_uppercase(self, client):
        res = await client.post("/knowledge", json={"name": "CursoCDO", "content": "test"})
        assert res.status_code == 422

    async def test_create_invalid_starts_with_hyphen(self, client):
        res = await client.post("/knowledge", json={"name": "-bad-name", "content": "test"})
        assert res.status_code == 422


@pytest.mark.asyncio
class TestUpdateDoc:
    async def test_update_success(self, client, temp_knowledge_dir):
        (temp_knowledge_dir / "curso-cdo.md").write_text("old content")
        res = await client.put("/knowledge/curso-cdo", json={"content": "new content"})
        assert res.status_code == 200
        assert (temp_knowledge_dir / "curso-cdo.md").read_text() == "new content"

    async def test_update_not_found(self, client):
        res = await client.put("/knowledge/nao-existe", json={"content": "test"})
        assert res.status_code == 404


@pytest.mark.asyncio
class TestDeleteDoc:
    async def test_delete_success(self, client, temp_knowledge_dir):
        (temp_knowledge_dir / "faq.md").write_text("to delete")
        res = await client.delete("/knowledge/faq")
        assert res.status_code == 200
        assert not (temp_knowledge_dir / "faq.md").exists()

    async def test_delete_not_found(self, client):
        res = await client.delete("/knowledge/nao-existe")
        assert res.status_code == 404


@pytest.mark.asyncio
class TestPathTraversal:
    async def test_traversal_get(self, client):
        res = await client.get("/knowledge/..%2F.env")
        assert res.status_code in (404, 422)  # Starlette may reject before handler

    async def test_traversal_create(self, client):
        res = await client.post("/knowledge", json={"name": "../../etc/passwd", "content": "x"})
        assert res.status_code == 422

    async def test_traversal_slashes(self, client):
        res = await client.post("/knowledge", json={"name": "sub/path", "content": "x"})
        assert res.status_code == 422
