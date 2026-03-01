import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Analise a conversa abaixo e gere um resumo da situação estratégica em 2-3 frases.

O resumo deve descrever:
- Estágio da conversa (primeiro contato, qualificação, recomendação, objeção, fechamento)
- Perfil aparente do cliente (técnico, leigo, indeciso, objetivo claro, etc.)
- O que já foi discutido ou qualificado
- Qual o movimento estratégico esperado agora

Responda APENAS com o texto do resumo, sem formatação extra."""


async def generate_situation_summary(
    conversation_history: str,
    contact_name: str = "",
) -> str:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    user_content = ""
    if contact_name:
        user_content += f"Cliente: {contact_name}\n\n"
    user_content += f"Conversa:\n{conversation_history}"

    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=256,
        system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text.strip()
