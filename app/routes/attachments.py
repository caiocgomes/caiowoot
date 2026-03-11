import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.database import get_db

router = APIRouter()

ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "attachments"
SENT_ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "attachments"


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


@router.get("/api/recent-attachments")
async def list_recent_attachments():
    """List unique recently sent attachments (most recent first, max 10)."""
    db = await get_db()
    try:
        rows = await db.execute(
            """SELECT media_url FROM messages
               WHERE direction = 'outbound' AND media_url IS NOT NULL
               ORDER BY created_at DESC"""
        )
        all_rows = await rows.fetchall()
    finally:
        await db.close()

    seen = set()
    results = []
    for row in all_rows:
        media_url = row["media_url"]
        stored_filename = Path(media_url).name
        # Strip {msg_id}_ prefix to get original filename
        original = re.sub(r"^\d+_", "", stored_filename)
        if original in seen:
            continue
        seen.add(original)
        # Verify file still exists on disk
        file_path = SENT_ATTACHMENTS_DIR / stored_filename
        if file_path.exists():
            results.append({"filename": original, "stored": stored_filename})
        if len(results) >= 10:
            break

    return results


@router.get("/api/recent-attachments/{stored_filename}")
async def get_recent_attachment(stored_filename: str):
    if ".." in stored_filename or "/" in stored_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = SENT_ATTACHMENTS_DIR / stored_filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
