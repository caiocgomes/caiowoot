import logging

import anthropic

from app.config import settings
from app.database import get_db
from app.services.smart_retrieval import index_edit_pair

logger = logging.getLogger(__name__)

ANNOTATION_PROMPT = """Analise a interação abaixo entre a IA e o operador humano.

Seu objetivo é entender a DECISÃO ESTRATÉGICA por trás da edição (ou aceitação) do operador.
Foque no raciocínio de vendas (quando qualificar, quando recomendar, quando recuar, como lidar com objeção), NÃO em diferenças de estilo textual (tom, comprimento, escolha de palavras).

Se o operador editou:
- Descreva o que a IA propôs vs. o que o operador fez
- Explique a correção estratégica (ex: "IA recomendou curso direto, operador voltou para qualificação")
- Identifique a situação que motivou a correção

Se o operador aceitou sem editar:
- Descreva a abordagem que funcionou
- Note que foi validada por aceitação

Responda em 2-3 frases, direto ao ponto. Apenas o texto da anotação, sem formatação."""


async def _get_annotation_prompt() -> str:
    try:
        from app.services.prompt_config import get_all_prompts
        prompts = await get_all_prompts()
        return prompts.get("annotation_prompt", ANNOTATION_PROMPT)
    except Exception:
        return ANNOTATION_PROMPT


async def generate_annotation(
    edit_pair_id: int,
    customer_message: str,
    original_draft: str,
    final_message: str,
    was_edited: bool,
    situation_summary: str | None = None,
    attachment_filename: str | None = None,
):
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        system = await _get_annotation_prompt()

        user_content = ""
        if situation_summary:
            user_content += f"Situação: {situation_summary}\n\n"
        user_content += f"Mensagem do cliente: {customer_message}\n\n"
        user_content += f"Draft da IA: {original_draft}\n\n"
        if was_edited:
            user_content += f"Operador enviou (editado): {final_message}"
        else:
            user_content += f"Operador enviou (sem edição): {final_message}"
        if attachment_filename:
            user_content += f"\nOperador anexou: {attachment_filename}"

        response = await client.messages.create(
            model=settings.claude_haiku_model,
            max_tokens=256,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        annotation = response.content[0].text.strip()

        # Save annotation to edit pair
        db = await get_db()
        try:
            await db.execute(
                "UPDATE edit_pairs SET strategic_annotation = ? WHERE id = ?",
                (annotation, edit_pair_id),
            )
            await db.commit()

            # Index in ChromaDB for future retrieval
            if situation_summary:
                index_edit_pair(
                    edit_pair_id=edit_pair_id,
                    situation_summary=situation_summary,
                    was_edited=was_edited,
                )
        finally:
            await db.close()

        logger.info("Strategic annotation generated for edit_pair %d", edit_pair_id)

    except Exception:
        logger.exception("Failed to generate strategic annotation for edit_pair %d", edit_pair_id)
