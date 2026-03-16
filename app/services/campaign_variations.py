import logging

from app.config import settings
from app.services.claude_client import get_anthropic_client

logger = logging.getLogger(__name__)


async def generate_variations(base_message: str, count: int = 8) -> list[str]:
    """Generate message variations using Claude Haiku for anti-spam diversity."""
    client = get_anthropic_client()

    prompt = f"""Você precisa criar {count} variações de uma mensagem de WhatsApp para envio em massa.

REGRAS CRÍTICAS:
- Cada variação deve transmitir EXATAMENTE a mesma informação e call-to-action
- As variações devem ser GENUINAMENTE diferentes, não apenas trocar sinônimos
- Varie: estrutura das frases, ordem dos parágrafos, abertura/fechamento, tom (mais formal/informal), uso de emoji, comprimento
- Se a mensagem contiver placeholders como {{{{nome}}}}, mantenha-os EXATAMENTE como estão
- Cada variação deve parecer escrita por uma pessoa diferente
- Mantenha o tom geral de vendas/marketing brasileiro, natural e conversacional

MENSAGEM BASE:
{base_message}

Retorne EXATAMENTE {count} variações, separadas por "---VARIACAO---" (sem nenhum outro texto antes, depois ou entre elas, apenas o texto de cada variação separado pelo delimitador)."""

    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    variations = [v.strip() for v in raw.split("---VARIACAO---") if v.strip()]

    # Ensure we have the right count
    if len(variations) < count:
        logger.warning("Claude returned %d variations instead of %d", len(variations), count)

    return variations[:count]
