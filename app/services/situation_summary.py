import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Analise a conversa abaixo e gere um resumo da situação estratégica.

Responda em JSON com exatamente 3 campos:
- "summary": resumo em 2-3 frases descrevendo estágio da conversa, perfil do cliente, o que foi discutido e próximo movimento esperado
- "product": identificador do produto de interesse do cliente, ou null se ainda não identificado. Valores possíveis: "curso-llm", "curso-zero-a-analista", "curso-cdo", "ai-para-influencers", null
- "stage": etapa do funil de vendas. Valores possíveis: "qualifying", "decided", "handbook_sent", "link_sent", "purchased", null

Responda APENAS com o JSON, sem markdown, sem formatação extra."""


async def _get_summary_prompt() -> str:
    try:
        from app.services.prompt_config import get_all_prompts
        prompts = await get_all_prompts()
        return prompts.get("summary_prompt", SUMMARY_PROMPT)
    except Exception:
        return SUMMARY_PROMPT


async def generate_situation_summary(
    conversation_history: str,
    contact_name: str = "",
) -> dict:
    """Generate structured situation summary.

    Returns dict with keys: summary (str), product (str|None), stage (str|None).
    On JSON parse failure, returns summary as raw text with product/stage as None.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    system = await _get_summary_prompt()

    user_content = ""
    if contact_name:
        user_content += f"Cliente: {contact_name}\n\n"
    user_content += f"Conversa:\n{conversation_history}"

    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()

    try:
        parsed = json.loads(raw)
        return {
            "summary": parsed.get("summary", raw),
            "product": parsed.get("product"),
            "stage": parsed.get("stage"),
        }
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Failed to parse situation summary JSON, using raw text")
        return {"summary": raw, "product": None, "stage": None}
