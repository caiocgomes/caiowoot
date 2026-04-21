import asyncio
import logging
import uuid

import anthropic

from app.config import settings
from app.database import get_db
from app.services.prompt_logger import save_prompt

# Re-export from prompt_builder for backward compatibility with tests
from app.services.prompt_builder import (
    ATTACHMENTS_DIR,
    ATTACHMENT_SECTION,
    RESPONSE_FORMAT_SECTION,
    TEMPORAL_CONTEXT_SECTION,
    WHATSAPP_FORMAT_SECTION,
    build_conversation_history as _build_conversation_history,
    build_fewshot_fallback as _build_fewshot_fallback,
    build_fewshot_from_retrieval as _build_fewshot_from_retrieval,
    build_prompt_parts as _build_prompt_parts,
    build_rules_section as _build_rules_section,
    build_system_prompt as _build_system_prompt,
    build_temporal_context as _build_temporal_context,
    get_approach_modifiers as _get_approach_modifiers,
    list_known_attachments,
)

# Re-export from claude_client for backward compatibility with tests
from app.services.claude_client import (
    DRAFT_TOOL,
    DRAFT_TOOL_NAME,
    call_haiku as _call_haiku,
    extract_tool_response as _extract_tool_response,
    validate_suggested_attachment as _validate_suggested_attachment,
)

# Re-export services used by prompt_builder so test patches on
# "app.services.draft_engine.<name>" continue to work.
from app.services.situation_summary import generate_situation_summary  # noqa: F401
from app.services.smart_retrieval import retrieve_similar  # noqa: F401
from app.services.learned_rules import get_active_rules  # noqa: F401
from app.services.knowledge import load_knowledge_base  # noqa: F401

logger = logging.getLogger(__name__)

# Keep legacy constants for backward compatibility with tests that reference them
SYSTEM_PROMPT = None  # Now built dynamically via _build_system_prompt()
APPROACH_MODIFIERS = None  # Now built dynamically via _get_approach_modifiers()


async def _generate_draft_group(
    db,
    conversation_id: int,
    trigger_message_id: int,
    approach_modifiers: list[tuple[str, str]],
    user_content: str,
    system_prompt: str,
    rules_section: str,
    knowledge_section: str,
    situation_summary: str | None,
    prompt_hash: str,
    operator_instruction: str | None,
    draft_group_id: str,
) -> list[dict]:
    """Generate a full set of draft variations and insert them into the DB."""
    tasks = [
        _call_haiku(user_content, modifier, system_prompt, rules_section, knowledge_section)
        for _, modifier in approach_modifiers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    drafts = []
    for i, (approach_name, _) in enumerate(approach_modifiers):
        if isinstance(results[i], Exception):
            logger.error("Draft variation %d failed: %s", i, results[i])
            draft_text = "(Erro ao gerar esta variação)"
            justification = str(results[i])
            suggested_attachment = None
        else:
            draft_text, justification, suggested_attachment = results[i]

        cursor = await db.execute(
            """INSERT INTO drafts
               (conversation_id, trigger_message_id, draft_text, justification,
                draft_group_id, variation_index, approach, prompt_hash, operator_instruction,
                situation_summary, suggested_attachment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, trigger_message_id, draft_text, justification,
             draft_group_id, i, approach_name, prompt_hash, operator_instruction,
             situation_summary, suggested_attachment),
        )
        drafts.append({
            "id": cursor.lastrowid,
            "conversation_id": conversation_id,
            "trigger_message_id": trigger_message_id,
            "draft_text": draft_text,
            "justification": justification,
            "status": "pending",
            "draft_group_id": draft_group_id,
            "variation_index": i,
            "approach": approach_name,
            "suggested_attachment": suggested_attachment,
        })

    return drafts


async def _broadcast_drafts(db, conversation_id: int, draft_group_id: str, drafts: list[dict], situation_summary: str | None):
    """Fetch funnel state and broadcast drafts_ready via WebSocket."""
    row = await db.execute(
        "SELECT funnel_product, funnel_stage FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    conv_row = await row.fetchone()

    from app.websocket_manager import manager
    await manager.broadcast(
        conversation_id,
        {
            "type": "drafts_ready",
            "conversation_id": conversation_id,
            "draft_group_id": draft_group_id,
            "drafts": drafts,
            "funnel_product": conv_row["funnel_product"] if conv_row else None,
            "funnel_stage": conv_row["funnel_stage"] if conv_row else None,
            "situation_summary": situation_summary,
        },
    )


async def generate_drafts(
    conversation_id: int,
    trigger_message_id: int,
    operator_instruction: str | None = None,
    proactive: bool = False,
    operator_name: str | None = None,
):
    db = await get_db()
    try:
        system_prompt = await _build_system_prompt(operator_name)
        approach_modifiers = await _get_approach_modifiers()

        user_content, situation_summary, rules_section, knowledge_section = await _build_prompt_parts(
            db, conversation_id, operator_instruction,
            proactive=proactive, operator_name=operator_name,
            trigger_message_id=trigger_message_id,
        )

        full_prompt = system_prompt + rules_section + knowledge_section + "\n\n" + user_content
        prompt_hash = save_prompt(full_prompt)

        draft_group_id = str(uuid.uuid4())

        drafts = await _generate_draft_group(
            db, conversation_id, trigger_message_id,
            approach_modifiers, user_content, system_prompt,
            rules_section, knowledge_section, situation_summary,
            prompt_hash, operator_instruction, draft_group_id,
        )

        await db.commit()
        await _broadcast_drafts(db, conversation_id, draft_group_id, drafts, situation_summary)

    except Exception:
        logger.exception("Failed to generate drafts for conversation %d", conversation_id)
    finally:
        await db.close()


async def regenerate_draft(
    conversation_id: int,
    trigger_message_id: int,
    draft_index: int | None = None,
    operator_instruction: str | None = None,
    proactive: bool = False,
    operator_name: str | None = None,
):
    db = await get_db()
    try:
        system_prompt = await _build_system_prompt(operator_name)
        approach_modifiers = await _get_approach_modifiers()

        user_content, situation_summary, rules_section, knowledge_section = await _build_prompt_parts(
            db, conversation_id, operator_instruction,
            proactive=proactive, operator_name=operator_name,
            trigger_message_id=trigger_message_id,
        )
        full_prompt = system_prompt + rules_section + knowledge_section + "\n\n" + user_content
        prompt_hash = save_prompt(full_prompt)

        if draft_index is not None:
            approach_name, modifier = approach_modifiers[draft_index]
            draft_text, justification, suggested_attachment = await _call_haiku(user_content, modifier, system_prompt, rules_section, knowledge_section)

            row = await db.execute(
                """SELECT id, draft_group_id FROM drafts
                   WHERE conversation_id = ? AND trigger_message_id = ? AND variation_index = ? AND status = 'pending'
                   ORDER BY created_at DESC LIMIT 1""",
                (conversation_id, trigger_message_id, draft_index),
            )
            existing = await row.fetchone()
            if existing:
                await db.execute(
                    """UPDATE drafts SET draft_text = ?, justification = ?, prompt_hash = ?, operator_instruction = ?, situation_summary = ?, suggested_attachment = ?
                       WHERE id = ?""",
                    (draft_text, justification, prompt_hash, operator_instruction, situation_summary, suggested_attachment, existing["id"]),
                )
                draft_group_id = existing["draft_group_id"]
            await db.commit()

            row = await db.execute(
                "SELECT * FROM drafts WHERE draft_group_id = ? ORDER BY variation_index",
                (draft_group_id,),
            )
            all_drafts = await row.fetchall()
            drafts = [{
                "id": d["id"], "conversation_id": d["conversation_id"],
                "trigger_message_id": d["trigger_message_id"],
                "draft_text": d["draft_text"], "justification": d["justification"],
                "status": d["status"], "draft_group_id": d["draft_group_id"],
                "variation_index": d["variation_index"], "approach": d["approach"],
                "suggested_attachment": d["suggested_attachment"],
            } for d in all_drafts]

        else:
            row = await db.execute(
                """SELECT draft_group_id FROM drafts
                   WHERE conversation_id = ? AND trigger_message_id = ? AND status = 'pending'
                   ORDER BY created_at DESC LIMIT 1""",
                (conversation_id, trigger_message_id),
            )
            existing = await row.fetchone()
            draft_group_id = existing["draft_group_id"] if existing else str(uuid.uuid4())

            await db.execute(
                "DELETE FROM drafts WHERE draft_group_id = ?",
                (draft_group_id,),
            )

            drafts = await _generate_draft_group(
                db, conversation_id, trigger_message_id,
                approach_modifiers, user_content, system_prompt,
                rules_section, knowledge_section, situation_summary,
                prompt_hash, operator_instruction, draft_group_id,
            )

            await db.commit()

        await _broadcast_drafts(db, conversation_id, draft_group_id, drafts, situation_summary)

    except Exception:
        logger.exception("Failed to regenerate drafts for conversation %d", conversation_id)
    finally:
        await db.close()
