"""Rotas do agente de reesquentamento de leads (antigo D-1)."""

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.config import now_local
from app.database import get_db_connection
from app.services.rewarm_engine import (
    decide_rewarm_action,
    default_reference_date,
    run_batch,
    select_rewarm_candidates,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Track background tasks so tests can await them. In production this set grows and
# entries auto-remove when done; memory footprint is negligible.
_background_tasks: set[asyncio.Task] = set()

# Nomes dos dias da semana em português, indexados por weekday() (0=segunda, 6=domingo)
_WEEKDAY_NAMES_PT = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


class ExecuteItem(BaseModel):
    conversation_id: int
    message: str


class ExecuteRequest(BaseModel):
    items: list[ExecuteItem]


class PreviewRequest(BaseModel):
    reference_date: str | None = None


def _validate_iso_date(s: str) -> str:
    """Valida 'YYYY-MM-DD'. Levanta HTTPException 422 se malformado."""
    try:
        return date.fromisoformat(s).isoformat()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"reference_date inválida: {exc}")


def _suggested_reference_date() -> tuple[str, str]:
    """Retorna (date_iso, label_pt) sugerido com base no dia da semana atual.

    - Segunda-feira: volta pra sexta passada (3 dias atrás).
    - Qualquer outro dia: ontem.
    Sem tratamento de feriado por decisão explícita (simplicidade).
    """
    today = now_local().date()
    if today.weekday() == 0:  # segunda
        ref = today - timedelta(days=3)  # sexta passada
    else:
        ref = today - timedelta(days=1)  # ontem
    label = _WEEKDAY_NAMES_PT[ref.weekday()]
    return ref.isoformat(), label


@router.get("/rewarm/suggested-date")
async def rewarm_suggested_date():
    """Sugere qual data de referência abrir no seletor, por padrão.

    Segunda → sexta passada; outros dias → ontem. Sem feriado.
    """
    ref_iso, label = _suggested_reference_date()
    return {"date": ref_iso, "label": label}


@router.post("/rewarm/preview")
async def rewarm_preview(
    req: PreviewRequest | None = None,
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    """Roda query + agente para cada candidata. Nunca envia mensagem.

    Body opcional: {"reference_date": "YYYY-MM-DD"}. Sem body, usa default (ontem).
    """
    if req is not None and req.reference_date:
        reference_date = _validate_iso_date(req.reference_date)
    else:
        reference_date = default_reference_date()

    candidates = await select_rewarm_candidates(db, reference_date=reference_date)
    if not candidates:
        return {"reference_date": reference_date, "items": []}

    async def decide(cand):
        decision = await decide_rewarm_action(cand["id"], db=db)
        return {
            "item_id": uuid.uuid4().hex,
            "conversation_id": cand["id"],
            "phone_number": cand["phone_number"],
            "contact_name": cand["contact_name"],
            "funnel_stage": cand["funnel_stage"],
            "action": decision["action"],
            "message": decision["message"],
            "reason": decision["reason"],
        }

    results = await asyncio.gather(*(decide(c) for c in candidates))
    return {"reference_date": reference_date, "items": list(results)}


@router.post("/rewarm/execute", status_code=202)
async def rewarm_execute(req: ExecuteRequest):
    """Dispara envio em batch em background e retorna 202 imediatamente."""
    items = [{"conversation_id": it.conversation_id, "message": it.message} for it in req.items]
    task = asyncio.create_task(run_batch(items, sent_by="rewarm_reviewed"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return Response(status_code=202)
