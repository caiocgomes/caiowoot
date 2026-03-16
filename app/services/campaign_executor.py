import asyncio
import base64
import io
import logging
import random

from app.database import get_db
from app.services.evolution import send_text_message, send_media_message
from app.websocket_manager import manager

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds
MAX_CONSECUTIVE_FAILURES = 5


async def _recompress_image(image_path: str) -> tuple[str, str]:
    """Recompress JPEG with random quality to vary hash. Returns (base64_data, mime_type)."""
    from PIL import Image

    quality = random.randint(85, 95)
    img = Image.open(image_path)
    buf = io.BytesIO()

    if img.mode == "RGBA":
        img = img.convert("RGB")

    img.save(buf, format="JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64, "image/jpeg"


async def _pick_variation(db, campaign_id: int, exclude_variation_id: int | None = None):
    """Pick the least-used variation, optionally excluding one (for retries)."""
    exclude_clause = ""
    params = [campaign_id]
    if exclude_variation_id is not None:
        exclude_clause = "AND id != ?"
        params.append(exclude_variation_id)

    row = await db.execute(
        f"""SELECT id, variation_text FROM campaign_variations
            WHERE campaign_id = ? {exclude_clause}
            ORDER BY usage_count ASC, RANDOM()
            LIMIT 1""",
        params,
    )
    variation = await row.fetchone()
    if not variation:
        return None, None
    return variation["id"], variation["variation_text"]


def _resolve_placeholders(text: str, contact_name: str | None) -> str:
    """Replace {{nome}} and similar placeholders."""
    if contact_name:
        text = text.replace("{{nome}}", contact_name)
        text = text.replace("{{Nome}}", contact_name)
    return text


async def _send_one(campaign, contact, db):
    """Send a message to a single contact. Returns True on success."""
    campaign_id = campaign["id"]
    contact_id = contact["id"]

    # Pick variation (exclude previous if retry)
    prev_variation_id = contact["variation_id"]
    variation_id, variation_text = await _pick_variation(db, campaign_id, prev_variation_id)

    if not variation_text:
        logger.error("No variation found for campaign %d", campaign_id)
        return False

    # Resolve placeholders
    message_text = _resolve_placeholders(variation_text, contact["name"])

    try:
        if campaign["image_path"]:
            b64_data, mime_type = await _recompress_image(campaign["image_path"])
            await send_media_message(contact["phone_number"], b64_data, mime_type, message_text)
        else:
            await send_text_message(contact["phone_number"], message_text)

        # Mark contact as sent
        await db.execute(
            """UPDATE campaign_contacts
               SET status = 'sent', variation_id = ?, sent_at = datetime('now')
               WHERE id = ?""",
            (variation_id, contact_id),
        )

        # Increment variation usage count
        await db.execute(
            "UPDATE campaign_variations SET usage_count = usage_count + 1 WHERE id = ?",
            (variation_id,),
        )

        # Reset consecutive failures
        await db.execute(
            "UPDATE campaigns SET consecutive_failures = 0 WHERE id = ?",
            (campaign_id,),
        )

        await db.commit()

        # Get updated counts
        counts = await _get_counts(db, campaign_id)

        await manager.broadcast(
            0,
            {
                "type": "campaign_progress",
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "status": "sent",
                **counts,
            },
        )

        return True

    except Exception as e:
        logger.exception("Failed to send campaign message to %s", contact["phone_number"])

        await db.execute(
            """UPDATE campaign_contacts
               SET status = 'failed', variation_id = ?, error_message = ?
               WHERE id = ?""",
            (variation_id, str(e)[:200], contact_id),
        )

        # Increment consecutive failures
        await db.execute(
            "UPDATE campaigns SET consecutive_failures = consecutive_failures + 1 WHERE id = ?",
            (campaign_id,),
        )
        await db.commit()

        # Check for auto-pause
        row = await db.execute(
            "SELECT consecutive_failures FROM campaigns WHERE id = ?",
            (campaign_id,),
        )
        camp = await row.fetchone()

        counts = await _get_counts(db, campaign_id)

        if camp and camp["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES:
            await db.execute(
                "UPDATE campaigns SET status = 'blocked', next_send_at = NULL WHERE id = ?",
                (campaign_id,),
            )
            await db.commit()

            await manager.broadcast(
                0,
                {
                    "type": "campaign_status",
                    "campaign_id": campaign_id,
                    "status": "blocked",
                },
            )
            logger.warning("Campaign %d auto-paused after %d consecutive failures", campaign_id, MAX_CONSECUTIVE_FAILURES)
        else:
            await manager.broadcast(
                0,
                {
                    "type": "campaign_progress",
                    "campaign_id": campaign_id,
                    "contact_id": contact_id,
                    "status": "failed",
                    "error": str(e)[:200],
                    **counts,
                },
            )

        return False


async def _get_counts(db, campaign_id: int) -> dict:
    """Get sent/failed/pending counts for a campaign."""
    row = await db.execute(
        """SELECT
            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_count,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
           FROM campaign_contacts WHERE campaign_id = ?""",
        (campaign_id,),
    )
    counts = await row.fetchone()
    return {
        "sent_count": counts["sent_count"] or 0,
        "failed_count": counts["failed_count"] or 0,
        "pending_count": counts["pending_count"] or 0,
    }


async def _process_campaigns():
    """Find and process due campaigns."""
    db = await get_db()
    try:
        rows = await db.execute(
            """SELECT id, name, status, image_path, min_interval, max_interval, consecutive_failures
               FROM campaigns
               WHERE status = 'running'
                 AND next_send_at IS NOT NULL
                 AND replace(next_send_at, 'T', ' ') <= datetime('now')"""
        )
        campaigns = await rows.fetchall()

        for campaign in campaigns:
            campaign_id = campaign["id"]

            # Get next pending contact
            contact_row = await db.execute(
                """SELECT id, phone_number, name, variation_id
                   FROM campaign_contacts
                   WHERE campaign_id = ? AND status = 'pending'
                   ORDER BY id
                   LIMIT 1""",
                (campaign_id,),
            )
            contact = await contact_row.fetchone()

            if not contact:
                # No more pending contacts - mark complete
                await db.execute(
                    "UPDATE campaigns SET status = 'completed', next_send_at = NULL WHERE id = ?",
                    (campaign_id,),
                )
                await db.commit()

                await manager.broadcast(
                    0,
                    {
                        "type": "campaign_status",
                        "campaign_id": campaign_id,
                        "status": "completed",
                    },
                )
                continue

            # Send to this contact
            await _send_one(campaign, contact, db)

            # Reload campaign status (might have been blocked)
            status_row = await db.execute(
                "SELECT status FROM campaigns WHERE id = ?", (campaign_id,)
            )
            current = await status_row.fetchone()

            if current and current["status"] == "running":
                # Schedule next send
                delay = random.randint(campaign["min_interval"], campaign["max_interval"])
                await db.execute(
                    "UPDATE campaigns SET next_send_at = datetime('now', '+' || ? || ' seconds') WHERE id = ?",
                    (delay, campaign_id),
                )
                await db.commit()
    finally:
        await db.close()


async def campaign_executor_loop():
    """Background polling loop for campaign execution."""
    logger.info("Campaign executor started (polling every %ds)", POLL_INTERVAL)
    while True:
        try:
            await _process_campaigns()
        except Exception:
            logger.exception("Error in campaign executor loop")
        await asyncio.sleep(POLL_INTERVAL)
