import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

KNOWLEDGE_DIR = Path("knowledge")
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _validate_name(name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise HTTPException(
            status_code=422,
            detail="Nome inválido. Use apenas letras minúsculas, números e hífens.",
        )


def _doc_path(name: str) -> Path:
    _validate_name(name)
    return KNOWLEDGE_DIR / f"{name}.md"


class DocCreate(BaseModel):
    name: str
    content: str


class DocUpdate(BaseModel):
    content: str


@router.get("/knowledge")
async def list_docs():
    if not KNOWLEDGE_DIR.exists():
        return []
    docs = []
    for f in sorted(KNOWLEDGE_DIR.glob("*.md")):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
        docs.append({"name": f.stem, "modified_at": mtime})
    return docs


@router.get("/knowledge/{name}")
async def get_doc(name: str):
    path = _doc_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"name": name, "content": path.read_text(encoding="utf-8")}


@router.post("/knowledge", status_code=201)
async def create_doc(body: DocCreate):
    path = _doc_path(body.name)
    if path.exists():
        raise HTTPException(status_code=409, detail="Documento já existe")
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    return {"name": body.name}


@router.put("/knowledge/{name}")
async def update_doc(name: str, body: DocUpdate):
    path = _doc_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    path.write_text(body.content, encoding="utf-8")
    return {"name": name}


@router.delete("/knowledge/{name}")
async def delete_doc(name: str):
    path = _doc_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    path.unlink()
    return {"name": name}
