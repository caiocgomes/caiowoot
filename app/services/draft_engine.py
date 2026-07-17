import asyncio
import logging
import time
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

# Lock por conversa para a seção crítica do regenerate-all: serializa o swap
# INSERT novo grupo + DELETE dos antigos, evitando estados com 0 ou 2 grupos.
_regenerate_locks: dict[int, asyncio.Lock] = {}


def _regenerate_lock(conversation_id: int) -> asyncio.Lock:
    lock = _regenerate_locks.get(conversation_id)
    if lock is None:
        lock = asyncio.Lock()
        _regenerate_locks[conversation_id] = lock
    return lock


async def _call_variations(
    approach_modifiers: list[tuple[str, str]],
    user_content: str,
    system_prompt: str,
    rules_section: str,
    knowledge_section: str,
) -> list:
    """Dispara as chamadas Haiku das variações em paralelo."""
    tasks = [
        _call_haiku(user_content, modifier, system_prompt, rules_section, knowledge_section)
        for _, modifier in approach_modifiers
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def _insert_draft_group(
    db,
    conversation_id: int,
    trigger_message_id: int,
    approach_modifiers: list[tuple[str, str]],
    results: list,
    situation_summary: str | None,
    prompt_hash: str,
    operator_instruction: str | None,
    draft_group_id: str,
) -> list[dict]:
    """Insere no banco os drafts de um grupo a partir dos resultados das variações."""
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


async def _broadcast_generating(conversation_id: int, trigger_message_id: int, draft_index: int | None):
    """Sinaliza ao frontend que uma geração começou (antes de qualquer chamada LLM)."""
    from app.websocket_manager import manager
    await manager.broadcast(
        conversation_id,
        {
            "type": "drafts_generating",
            "conversation_id": conversation_id,
            "trigger_message_id": trigger_message_id,
            "draft_index": draft_index,
        },
    )


async def _broadcast_error(conversation_id: int, trigger_message_id: int, exc: Exception):
    """Sinaliza falha de geração; falha do próprio broadcast não pode propagar."""
    try:
        from app.websocket_manager import manager
        await manager.broadcast(
            conversation_id,
            {
                "type": "drafts_error",
                "conversation_id": conversation_id,
                "trigger_message_id": trigger_message_id,
                "error": str(exc)[:200],
            },
        )
    except Exception:
        logger.exception("Failed to broadcast drafts_error for conversation %d", conversation_id)


async def _load_stored_summary(db, conversation_id: int) -> str | None:
    """Resumo de situação não-nulo mais recente já armazenado nos drafts da conversa."""
    row = await db.execute(
        """SELECT situation_summary FROM drafts
           WHERE conversation_id = ? AND situation_summary IS NOT NULL AND situation_summary != ''
           ORDER BY created_at DESC, id DESC LIMIT 1""",
        (conversation_id,),
    )
    found = await row.fetchone()
    return found["situation_summary"] if found else None


def _log_timing(
    conversation_id: int,
    draft_group_id: str,
    timings: dict,
    llm_ms: float,
    commit_ms: float,
    start: float,
):
    total_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "draft_timing conv=%d group=%s summary_ms=%d retrieval_ms=%d llm_ms=%d commit_ms=%d total_ms=%d",
        conversation_id,
        draft_group_id,
        timings.get("summary_ms", 0),
        timings.get("retrieval_ms", 0),
        llm_ms,
        commit_ms,
        total_ms,
    )
    if commit_ms > 100:
        logger.warning(
            "Commit lento na geração de drafts: %dms (conv=%d group=%s)",
            commit_ms, conversation_id, draft_group_id,
        )


async def generate_drafts(
    conversation_id: int,
    trigger_message_id: int,
    operator_instruction: str | None = None,
    proactive: bool = False,
    operator_name: str | None = None,
):
    start = time.perf_counter()
    db = await get_db()
    try:
        await _broadcast_generating(conversation_id, trigger_message_id, None)

        system_prompt = await _build_system_prompt(operator_name)
        approach_modifiers = await _get_approach_modifiers()

        timings: dict = {}
        user_content, situation_summary, rules_section, knowledge_section = await _build_prompt_parts(
            db, conversation_id, operator_instruction,
            proactive=proactive, operator_name=operator_name,
            trigger_message_id=trigger_message_id,
            timings=timings,
        )

        full_prompt = system_prompt + rules_section + knowledge_section + "\n\n" + user_content
        prompt_hash = await asyncio.to_thread(save_prompt, full_prompt)

        draft_group_id = str(uuid.uuid4())

        llm_start = time.perf_counter()
        results = await _call_variations(
            approach_modifiers, user_content, system_prompt, rules_section, knowledge_section,
        )
        llm_ms = (time.perf_counter() - llm_start) * 1000

        drafts = await _insert_draft_group(
            db, conversation_id, trigger_message_id,
            approach_modifiers, results, situation_summary,
            prompt_hash, operator_instruction, draft_group_id,
        )

        commit_start = time.perf_counter()
        await db.commit()
        commit_ms = (time.perf_counter() - commit_start) * 1000

        _log_timing(conversation_id, draft_group_id, timings, llm_ms, commit_ms, start)
        await _broadcast_drafts(db, conversation_id, draft_group_id, drafts, situation_summary)

    except Exception as exc:
        logger.exception("Failed to generate drafts for conversation %d", conversation_id)
        await _broadcast_error(conversation_id, trigger_message_id, exc)
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
    start = time.perf_counter()
    db = await get_db()
    try:
        await _broadcast_generating(conversation_id, trigger_message_id, draft_index)

        system_prompt = await _build_system_prompt(operator_name)
        approach_modifiers = await _get_approach_modifiers()

        # Reusa o resumo já armazenado: regenerar não muda a situação da conversa
        # e economiza uma chamada LLM inteira antes das variações.
        stored_summary = await _load_stored_summary(db, conversation_id)

        timings: dict = {}
        user_content, situation_summary, rules_section, knowledge_section = await _build_prompt_parts(
            db, conversation_id, operator_instruction,
            situation_summary=stored_summary,
            proactive=proactive, operator_name=operator_name,
            trigger_message_id=trigger_message_id,
            timings=timings,
        )
        full_prompt = system_prompt + rules_section + knowledge_section + "\n\n" + user_content
        prompt_hash = await asyncio.to_thread(save_prompt, full_prompt)

        if draft_index is not None:
            approach_name, modifier = approach_modifiers[draft_index]
            llm_start = time.perf_counter()
            draft_text, justification, suggested_attachment = await _call_haiku(user_content, modifier, system_prompt, rules_section, knowledge_section)
            llm_ms = (time.perf_counter() - llm_start) * 1000

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
            commit_start = time.perf_counter()
            await db.commit()
            commit_ms = (time.perf_counter() - commit_start) * 1000

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
            # Swap atômico: gera com grupo NOVO, insere e só então remove os
            # grupos pending antigos na mesma transação — leitor nunca vê zero grupos.
            draft_group_id = str(uuid.uuid4())

            llm_start = time.perf_counter()
            results = await _call_variations(
                approach_modifiers, user_content, system_prompt, rules_section, knowledge_section,
            )
            llm_ms = (time.perf_counter() - llm_start) * 1000

            async with _regenerate_lock(conversation_id):
                drafts = await _insert_draft_group(
                    db, conversation_id, trigger_message_id,
                    approach_modifiers, results, situation_summary,
                    prompt_hash, operator_instruction, draft_group_id,
                )
                await db.execute(
                    """DELETE FROM drafts
                       WHERE conversation_id = ? AND trigger_message_id = ?
                         AND status = 'pending' AND draft_group_id != ?""",
                    (conversation_id, trigger_message_id, draft_group_id),
                )
                commit_start = time.perf_counter()
                await db.commit()
                commit_ms = (time.perf_counter() - commit_start) * 1000

        _log_timing(conversation_id, draft_group_id, timings, llm_ms, commit_ms, start)
        await _broadcast_drafts(db, conversation_id, draft_group_id, drafts, situation_summary)

    except Exception as exc:
        logger.exception("Failed to regenerate drafts for conversation %d", conversation_id)
        await _broadcast_error(conversation_id, trigger_message_id, exc)
    finally:
        await db.close()
