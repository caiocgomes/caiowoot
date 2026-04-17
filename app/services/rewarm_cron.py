"""Cron loops do rewarm D-1 automatizado.

- Slot matinal (10:30 local): seleciona candidatos, atribui braço via bandit, enfileira scheduled_send.
- Slot noturno (02:00 local): fecha dispatches stale, refita posterior.
- Idempotência via cron_runs (slot_key, DATE(ran_at) unique).
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from app.config import now_local, settings
from app.database import get_db
from app.services.rewarm_bandit import (
    close_stale_dispatches,
    compute_slot_datetime,
    extract_features,
    format_send_at_utc,
    refit_posterior,
    sample_arm,
)
from app.services.rewarm_engine import decide_rewarm_action, select_rewarm_candidates

logger = logging.getLogger(__name__)

# Slot -> (hora, minuto) em timezone local
CRON_SLOTS: dict[str, tuple[int, int]] = {
    "morning": (10, 30),
    "nightly": (2, 0),
}

POLL_INTERVAL = 60  # segundos


async def _slot_already_ran(db, slot_key: str, today_iso: str) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM cron_runs WHERE slot_key = ? AND DATE(ran_at) = ?",
        (slot_key, today_iso),
    )
    return (await cursor.fetchone()) is not None


async def _mark_slot_ran(db, slot_key: str) -> None:
    await db.execute(
        "INSERT INTO cron_runs (slot_key) VALUES (?)",
        (slot_key,),
    )
    await db.commit()


async def daily_dispatch() -> dict[str, Any]:
    """Slot matinal: seleciona, decide conteúdo, atribui braço, enfileira."""
    if not settings.rewarm_auto_send:
        logger.info("rewarm auto-send desligado; daily_dispatch no-op")
        return {"skipped": "flag_off", "sent": 0}

    db = await get_db()
    try:
        candidates = await select_rewarm_candidates(db)
    finally:
        await db.close()

    if not candidates:
        logger.info("rewarm daily_dispatch: sem candidatos")
        return {"skipped": "no_candidates", "sent": 0, "dispatched": 0}

    dispatched = 0
    agent_skipped = 0
    errors = 0

    for cand in candidates:
        conv_id = cand["id"]
        try:
            decision = await decide_rewarm_action(conv_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("rewarm decide failed conv=%s: %s", conv_id, exc)
            errors += 1
            continue

        if decision["action"] != "send" or not decision.get("message"):
            agent_skipped += 1
            logger.info("rewarm agent skip conv=%s reason=%s", conv_id, decision.get("reason", ""))
            continue

        db = await get_db()
        try:
            features = await extract_features(db, conv_id)
            arm = await sample_arm(db, features)
            send_at_local = compute_slot_datetime(arm)
            send_at_iso = format_send_at_utc(send_at_local)

            send_cursor = await db.execute(
                """INSERT INTO scheduled_sends (conversation_id, content, send_at, status, created_by)
                   VALUES (?, ?, ?, 'pending', 'rewarm_agent')""",
                (conv_id, decision["message"], send_at_iso),
            )
            scheduled_send_id = send_cursor.lastrowid

            await db.execute(
                """INSERT INTO rewarm_dispatches
                   (conversation_id, features_json, arm, scheduled_send_id, scheduled_for, status)
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (
                    conv_id,
                    json.dumps(features),
                    arm,
                    scheduled_send_id,
                    send_at_iso,
                ),
            )
            await db.commit()
            dispatched += 1
            logger.info(
                "rewarm dispatched conv=%s arm=%s send_at=%s scheduled_send=%s",
                conv_id, arm, send_at_iso, scheduled_send_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("rewarm dispatch enqueue failed conv=%s: %s", conv_id, exc)
            errors += 1
        finally:
            await db.close()

    return {
        "candidates": len(candidates),
        "dispatched": dispatched,
        "agent_skipped": agent_skipped,
        "errors": errors,
    }


async def nightly_closeout() -> dict[str, Any]:
    """Slot noturno: fecha dispatches stale (48h sem resposta) e refita posterior."""
    db = await get_db()
    try:
        closed = await close_stale_dispatches(db)
        stats = await refit_posterior(db)
    finally:
        await db.close()

    logger.info("rewarm nightly_closeout closed=%s refit=%s", closed, stats)
    return {"closed": closed, "refit": stats}


async def _maybe_run_slot(slot_key: str, runner) -> None:
    now = now_local()
    hour, minute = CRON_SLOTS[slot_key]
    if now.hour != hour or now.minute < minute:
        return
    today_iso = now.strftime("%Y-%m-%d")

    db = await get_db()
    try:
        if await _slot_already_ran(db, slot_key, today_iso):
            return
    finally:
        await db.close()

    logger.info("rewarm cron running slot=%s", slot_key)
    try:
        result = await runner()
    except Exception:
        logger.exception("rewarm cron slot %s failed", slot_key)
        return

    db = await get_db()
    try:
        await _mark_slot_ran(db, slot_key)
    finally:
        await db.close()

    logger.info("rewarm cron slot=%s done result=%s", slot_key, result)


async def rewarm_cron_loop() -> None:
    """Lifespan task: dispara slots matinal e noturno quando bate a hora local."""
    logger.info("rewarm_cron_loop started")
    while True:
        try:
            await _maybe_run_slot("morning", daily_dispatch)
            await _maybe_run_slot("nightly", nightly_closeout)
        except Exception:
            logger.exception("rewarm_cron_loop tick error")
        await asyncio.sleep(POLL_INTERVAL)
