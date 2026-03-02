import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

REWRITE_TOOL_NAME = "rewritten_text"

REWRITE_TOOL = {
    "name": REWRITE_TOOL_NAME,
    "description": "Retorna o texto reescrito.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "O texto reescrito.",
            },
        },
        "required": ["text"],
    },
}

SYSTEM_PROMPT = """Você é um assistente de escrita para WhatsApp. Sua tarefa é reescrever o texto do operador mantendo exatamente as mesmas ideias e informações.

Regras:
- Corrija erros de português (gramática, ortografia, concordância)
- Melhore a clareza e fluidez das frases
- Mantenha tom natural de WhatsApp: direto, amigável, não corporativo
- NÃO adicione informações que não estavam no texto original
- NÃO remova informações que estavam no texto original
- NÃO mude o significado ou a intenção do texto
- NÃO use markdown, HTML ou formatação especial (só formatação WhatsApp: *negrito*, _itálico_)
- Siga de perto a estrutura e o caminho argumentativo do texto original
- Use a tool rewritten_text para retornar o resultado"""


async def rewrite_text(text: str) -> str:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[REWRITE_TOOL],
        tool_choice={"type": "tool", "name": REWRITE_TOOL_NAME},
        messages=[{"role": "user", "content": text}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == REWRITE_TOOL_NAME:
            return block.input.get("text", text)
    # Fallback: return text block if no tool_use
    for block in response.content:
        if hasattr(block, "text"):
            return block.text.strip()
    return text
