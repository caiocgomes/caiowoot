import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "attachments"


@router.get("/api/attachments")
async def list_attachments():
    if not ATTACHMENTS_DIR.exists():
        return []
    return sorted(f.name for f in ATTACHMENTS_DIR.iterdir() if f.is_file())


@router.get("/api/attachments/{filename}")
async def get_attachment(filename: str):
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = ATTACHMENTS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
