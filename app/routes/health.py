from fastapi import APIRouter

from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    db_ok = False
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        await db.close()
        db_ok = True
    except Exception:
        pass

    return {"status": "ok" if db_ok else "unhealthy", "db": db_ok}
