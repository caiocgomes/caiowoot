import asyncio
import logging

from app.database import get_db
from app.services.send_executor import execute_send
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


async def _process_due_sends():
    """Find and send all due scheduled messages."""
    db = await get_db()
    try:
        # Atomically transition pending -> sending for due messages
        await db.execute(
            """UPDATE scheduled_sends
               SET status = 'sending'
               WHERE status = 'pending'
                 AND replace(send_at, 'T', ' ') <= datetime('now')"""
        )
        await db.commit()

        # Fetch all messages now in 'sending' state
        rows = await db.execute(
            """SELECT id, conversation_id, content, draft_id, draft_group_id,
                      selected_draft_index, created_by, send_at
               FROM scheduled_sends
               WHERE status = 'sending'"""
        )
        sends = await rows.fetchall()
    finally:
        await db.close()

    for send in sends:
        try:
            await execute_send(
                conversation_id=send["conversation_id"],
                text=send["content"],
                operator=send["created_by"],
                draft_id=send["draft_id"],
                draft_group_id=send["draft_group_id"],
                selected_draft_index=send["selected_draft_index"],
            )

            # Mark as sent
            db2 = await get_db()
            try:
                await db2.execute(
                    """UPDATE scheduled_sends
                       SET status = 'sent', sent_at = datetime('now')
                       WHERE id = ?""",
                    (send["id"],),
                )
                if send["created_by"] == "rewarm_agent":
                    await db2.execute(
                        """UPDATE rewarm_dispatches
                           SET sent_at = datetime('now'), status = 'sent'
                           WHERE scheduled_send_id = ? AND sent_at IS NULL""",
                        (send["id"],),
                    )
                await db2.commit()
            finally:
                await db2.close()

            logger.info("Scheduled send %d completed for conversation %d", send["id"], send["conversation_id"])

        except Exception:
            logger.exception("Failed to execute scheduled send %d, reverting to pending", send["id"])
            # Revert to pending for retry on next cycle
            db3 = await get_db()
            try:
                await db3.execute(
                    "UPDATE scheduled_sends SET status = 'pending' WHERE id = ? AND status = 'sending'",
                    (send["id"],),
                )
                await db3.commit()
            finally:
                await db3.close()


async def scheduler_loop():
    """Background polling loop that runs every POLL_INTERVAL seconds."""
    logger.info("Scheduler loop started (polling every %ds)", POLL_INTERVAL)
    while True:
        try:
            await _process_due_sends()
        except Exception:
            logger.exception("Error in scheduler loop iteration")
        await asyncio.sleep(POLL_INTERVAL)
