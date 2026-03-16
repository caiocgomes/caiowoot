import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db_connection
from app.services.learned_rules import create_rule
from app.services.smart_retrieval import update_metadata

router = APIRouter()


class PromoteRequest(BaseModel):
    rule_text: str | None = None


@router.get("/review")
async def list_pending_annotations(db: aiosqlite.Connection = Depends(get_db_connection)):
    rows = await db.execute(
        """SELECT id, situation_summary, customer_message, original_draft, final_message,
                  was_edited, strategic_annotation, created_at
           FROM edit_pairs
           WHERE strategic_annotation IS NOT NULL AND validated = 0
           ORDER BY created_at DESC"""
    )
    annotations = [dict(r) for r in await rows.fetchall()]

    # Pending stats
    total_pending = len(annotations)
    total_edited = sum(1 for a in annotations if a["was_edited"])
    total_accepted = total_pending - total_edited

    # History stats
    hist = await db.execute(
        """SELECT
             SUM(CASE WHEN rejected = 0 THEN 1 ELSE 0 END) AS total_validated,
             SUM(CASE WHEN rejected = 1 THEN 1 ELSE 0 END) AS total_rejected
           FROM edit_pairs
           WHERE strategic_annotation IS NOT NULL AND validated = 1"""
    )
    hist_row = await hist.fetchone()
    promoted = await db.execute("SELECT COUNT(*) as c FROM learned_rules")
    promoted_row = await promoted.fetchone()

    return {
        "annotations": annotations,
        "stats": {
            "total_pending": total_pending,
            "total_edited": total_edited,
            "total_accepted": total_accepted,
        },
        "history_stats": {
            "total_validated": hist_row["total_validated"] or 0,
            "total_rejected": hist_row["total_rejected"] or 0,
            "total_promoted": promoted_row["c"] or 0,
        },
    }


@router.post("/review/{edit_pair_id}/validate")
async def validate_annotation(edit_pair_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    row = await db.execute("SELECT id FROM edit_pairs WHERE id = ?", (edit_pair_id,))
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Edit pair not found")

    await db.execute(
        "UPDATE edit_pairs SET validated = 1, rejected = 0 WHERE id = ?",
        (edit_pair_id,),
    )
    await db.commit()

    try:
        update_metadata(edit_pair_id, validated=True, rejected=False)
    except Exception:
        pass

    return {"status": "ok", "edit_pair_id": edit_pair_id, "action": "validated"}


@router.post("/review/{edit_pair_id}/reject")
async def reject_annotation(edit_pair_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    row = await db.execute("SELECT id FROM edit_pairs WHERE id = ?", (edit_pair_id,))
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Edit pair not found")

    await db.execute(
        "UPDATE edit_pairs SET validated = 1, rejected = 1 WHERE id = ?",
        (edit_pair_id,),
    )
    await db.commit()

    try:
        update_metadata(edit_pair_id, validated=True, rejected=True)
    except Exception:
        pass

    return {"status": "ok", "edit_pair_id": edit_pair_id, "action": "rejected"}


@router.post("/review/{edit_pair_id}/promote")
async def promote_annotation(edit_pair_id: int, db: aiosqlite.Connection = Depends(get_db_connection), req: PromoteRequest | None = None):
    row = await db.execute(
        "SELECT strategic_annotation FROM edit_pairs WHERE id = ?",
        (edit_pair_id,),
    )
    pair = await row.fetchone()
    if not pair:
        raise HTTPException(status_code=404, detail="Edit pair not found")
    if not pair["strategic_annotation"]:
        raise HTTPException(status_code=400, detail="No annotation to promote")

    rule_text = (req.rule_text if req and req.rule_text else pair["strategic_annotation"])

    await db.execute(
        "UPDATE edit_pairs SET validated = 1, rejected = 0 WHERE id = ?",
        (edit_pair_id,),
    )
    await db.commit()

    try:
        update_metadata(edit_pair_id, validated=True, rejected=False)
    except Exception:
        pass

    rule = await create_rule(rule_text, source_edit_pair_id=edit_pair_id, db=db)
    return {"status": "ok", "edit_pair_id": edit_pair_id, "action": "promoted", "rule": rule}
