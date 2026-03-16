import asyncio
import json

import aiosqlite
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.auth import get_operator_from_request, is_admin
from app.database import get_db, get_db_connection

router = APIRouter()


class AnalysisRequest(BaseModel):
    period_start: str | None = None
    period_end: str | None = None


def _check_admin(request: Request):
    operator = get_operator_from_request(request)
    return is_admin(operator)


@router.get("/admin/coaching")
async def coaching_page(request: Request):
    if not _check_admin(request):
        return RedirectResponse("/")
    return FileResponse("app/static/coaching.html")


@router.post("/admin/analysis/run")
async def trigger_analysis(request: Request, db: aiosqlite.Connection = Depends(get_db_connection), body: AnalysisRequest | None = None):
    if not _check_admin(request):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    if body and body.period_start and body.period_end:
        period_start = body.period_start
        period_end = body.period_end
    else:
        from app.config import now_local
        from datetime import timedelta
        yesterday = now_local() - timedelta(days=1)
        period_start = yesterday.strftime("%Y-%m-%d")
        period_end = period_start

    # Create run record so we can return the id immediately
    cursor = await db.execute(
        "INSERT INTO analysis_runs (period_start, period_end, status) VALUES (?, ?, 'running')",
        (period_start, period_end),
    )
    run_id = cursor.lastrowid
    await db.commit()

    # Process in background (uses its own connection)
    async def _run_in_background(run_id, period_start, period_end):
        from app.services.operator_coaching import _process_analysis
        bg_db = await get_db()
        try:
            await _process_analysis(bg_db, run_id, period_start, period_end)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Analysis run %d failed", run_id)
            await bg_db.execute(
                "UPDATE analysis_runs SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), run_id),
            )
            await bg_db.commit()
        finally:
            await bg_db.close()

    asyncio.create_task(_run_in_background(run_id, period_start, period_end))

    return {"run_id": run_id, "status": "running", "period_start": period_start, "period_end": period_end}


@router.get("/admin/analysis/status/{run_id}")
async def analysis_status(request: Request, run_id: int, db: aiosqlite.Connection = Depends(get_db_connection)):
    if not _check_admin(request):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    row = await db.execute(
        "SELECT * FROM analysis_runs WHERE id = ?", (run_id,)
    )
    run = await row.fetchone()
    if not run:
        return JSONResponse({"detail": "Run not found"}, status_code=404)

    # Count completed assessments
    row = await db.execute(
        "SELECT COUNT(*) as c FROM conversation_assessments WHERE analysis_run_id = ?",
        (run_id,),
    )
    count = await row.fetchone()

    return {
        "run_id": run["id"],
        "status": run["status"],
        "period_start": run["period_start"],
        "period_end": run["period_end"],
        "total_conversations": run["total_conversations"],
        "total_operators": run["total_operators"],
        "assessments_completed": count["c"],
        "error_message": run["error_message"],
        "created_at": run["created_at"],
        "completed_at": run["completed_at"],
    }


@router.get("/admin/analysis/results")
async def analysis_results(request: Request, db: aiosqlite.Connection = Depends(get_db_connection), run_id: int | None = None):
    if not _check_admin(request):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    # Get the run
    if run_id:
        row = await db.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,))
    else:
        row = await db.execute(
            "SELECT * FROM analysis_runs WHERE status = 'completed' ORDER BY created_at DESC LIMIT 1"
        )
    run = await row.fetchone()
    if not run:
        return {"run": None, "operator_digests": [], "salvageable_sales": [], "unanswered": []}

    run_data = {
        "id": run["id"],
        "status": run["status"],
        "period_start": run["period_start"],
        "period_end": run["period_end"],
        "total_conversations": run["total_conversations"],
        "total_operators": run["total_operators"],
        "created_at": run["created_at"],
        "completed_at": run["completed_at"],
    }

    # Get operator digests
    rows = await db.execute(
        "SELECT * FROM operator_digests WHERE analysis_run_id = ? AND operator_name != '__unanswered__'",
        (run["id"],),
    )
    digests_raw = await rows.fetchall()
    operator_digests = []
    all_salvageable = []

    for d in digests_raw:
        digest = {
            "operator_name": d["operator_name"],
            "summary": d["summary"],
            "patterns": json.loads(d["patterns_json"]) if d["patterns_json"] else [],
            "factual_issues": json.loads(d["factual_issues_json"]) if d["factual_issues_json"] else [],
            "salvageable_sales": json.loads(d["salvageable_sales_json"]) if d["salvageable_sales_json"] else [],
            "metrics": json.loads(d["metrics_json"]) if d["metrics_json"] else {},
        }
        operator_digests.append(digest)
        all_salvageable.extend(digest["salvageable_sales"])

    # Sort salvageable by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    all_salvageable.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

    # Get unanswered
    rows = await db.execute(
        "SELECT salvageable_sales_json FROM operator_digests WHERE analysis_run_id = ? AND operator_name = '__unanswered__'",
        (run["id"],),
    )
    unanswered_row = await rows.fetchone()
    unanswered = json.loads(unanswered_row["salvageable_sales_json"]) if unanswered_row and unanswered_row["salvageable_sales_json"] else []

    # Get individual conversation assessments grouped by operator
    rows = await db.execute(
        """SELECT ca.*, c.contact_name, c.phone_number
           FROM conversation_assessments ca
           JOIN conversations c ON c.id = ca.conversation_id
           WHERE ca.analysis_run_id = ?
           ORDER BY ca.operator_name, ca.created_at DESC""",
        (run["id"],),
    )
    assessments_raw = await rows.fetchall()
    assessments_by_operator = {}
    for a in assessments_raw:
        op = a["operator_name"] or "desconhecido"
        if op not in assessments_by_operator:
            assessments_by_operator[op] = []
        assessments_by_operator[op].append({
            "conversation_id": a["conversation_id"],
            "contact_name": a["contact_name"],
            "phone_number": a["phone_number"],
            "engagement_level": a["engagement_level"],
            "sale_status": a["sale_status"],
            "recovery_potential": a["recovery_potential"],
            "recovery_suggestion": a["recovery_suggestion"],
            "factual_issues": json.loads(a["factual_issues_json"]) if a["factual_issues_json"] else [],
            "overall_assessment": a["overall_assessment"],
            "metrics": json.loads(a["metrics_json"]) if a["metrics_json"] else {},
        })

    return {
        "run": run_data,
        "operator_digests": operator_digests,
        "salvageable_sales": all_salvageable,
        "unanswered": unanswered,
        "assessments_by_operator": assessments_by_operator,
    }
