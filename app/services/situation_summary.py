import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Analise a conversa abaixo e gere um resumo da situação estratégica.
Use a tool classify_conversation para retornar o resultado estruturado."""

CLASSIFY_TOOL = {
    "name": "classify_conversation",
    "description": "Classifica a conversa com resumo estratégico, produto de interesse e etapa do funil.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Resumo em 2-3 frases: estágio da conversa, perfil do cliente, o que foi discutido e próximo movimento esperado.",
            },
            "product": {
                "type": ["string", "null"],
                "enum": ["curso-llm", "curso-zero-a-analista", "curso-cdo", "ai-para-influencers", None],
                "description": "Identificador do produto de interesse do cliente, ou null se não identificado.",
            },
            "stage": {
                "type": ["string", "null"],
                "enum": ["qualifying", "decided", "handbook_sent", "link_sent", "purchased", None],
                "description": "Etapa do funil de vendas, ou null se não identificada.",
            },
        },
        "required": ["summary", "product", "stage"],
    },
}


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
    """Generate structured situation summary via tool use.

    Returns dict with keys: summary (str), product (str|None), stage (str|None).
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    system = await _get_summary_prompt()

    user_content = ""
    if contact_name:
        user_content += f"Cliente: {contact_name}\n\n"
    user_content += f"Conversa:\n{conversation_history}"

    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=1024,
        system=system,
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "classify_conversation"},
        messages=[{"role": "user", "content": user_content}],
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "classify_conversation":
            return {
                "summary": block.input.get("summary", ""),
                "product": block.input.get("product"),
                "stage": block.input.get("stage"),
            }

    # Fallback if no tool use (shouldn't happen with tool_choice forced)
    logger.warning("No tool_use block in response, falling back to empty")
    return {"summary": "", "product": None, "stage": None}
