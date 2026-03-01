from app.database import get_db


async def get_active_rules() -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT id, rule_text FROM learned_rules WHERE is_active = 1 ORDER BY created_at"
        )
        return [dict(r) for r in await rows.fetchall()]
    finally:
        await db.close()


async def get_all_rules() -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT id, rule_text, source_edit_pair_id, is_active, created_at, updated_at FROM learned_rules ORDER BY created_at"
        )
        return [dict(r) for r in await rows.fetchall()]
    finally:
        await db.close()


async def create_rule(rule_text: str, source_edit_pair_id: int | None = None) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO learned_rules (rule_text, source_edit_pair_id) VALUES (?, ?)",
            (rule_text, source_edit_pair_id),
        )
        await db.commit()
        row = await db.execute("SELECT * FROM learned_rules WHERE id = ?", (cursor.lastrowid,))
        return dict(await row.fetchone())
    finally:
        await db.close()


async def update_rule(rule_id: int, rule_text: str) -> dict | None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE learned_rules SET rule_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (rule_text, rule_id),
        )
        await db.commit()
        row = await db.execute("SELECT * FROM learned_rules WHERE id = ?", (rule_id,))
        result = await row.fetchone()
        return dict(result) if result else None
    finally:
        await db.close()


async def toggle_rule(rule_id: int) -> dict | None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE learned_rules SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (rule_id,),
        )
        await db.commit()
        row = await db.execute("SELECT * FROM learned_rules WHERE id = ?", (rule_id,))
        result = await row.fetchone()
        return dict(result) if result else None
    finally:
        await db.close()
