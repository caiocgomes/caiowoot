from app.database import get_db


async def get_profile(operator_name: str, db=None) -> dict | None:
    close_db = db is None
    if db is None:
        db = await get_db()
    try:
        row = await db.execute(
            "SELECT operator_name, display_name, context, updated_at FROM operator_profiles WHERE operator_name = ?",
            (operator_name,),
        )
        result = await row.fetchone()
        return dict(result) if result else None
    finally:
        if close_db:
            await db.close()


async def upsert_profile(operator_name: str, display_name: str, context: str, db=None) -> None:
    close_db = db is None
    if db is None:
        db = await get_db()
    try:
        await db.execute(
            "INSERT INTO operator_profiles (operator_name, display_name, context, updated_at) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(operator_name) DO UPDATE SET display_name = excluded.display_name, "
            "context = excluded.context, updated_at = CURRENT_TIMESTAMP",
            (operator_name, display_name, context),
        )
        await db.commit()
    finally:
        if close_db:
            await db.close()
