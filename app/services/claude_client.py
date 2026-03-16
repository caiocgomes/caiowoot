import logging
from pathlib import Path

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client = None

ATTACHMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge" / "attachments"

DRAFT_TOOL_NAME = "draft_response"

DRAFT_TOOL = {
    "name": DRAFT_TOOL_NAME,
    "description": "Retorna o draft de resposta para o cliente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "draft": {
                "type": "string",
                "description": "Texto da mensagem proposta para o cliente.",
            },
            "justification": {
                "type": "string",
                "description": "1-2 frases explicando por que você escolheu essa abordagem (isso NÃO vai pro cliente, é só pro operador).",
            },
            "suggested_attachment": {
                "type": ["string", "null"],
                "description": "Nome do arquivo de anexo sugerido (ex: handbook.pdf), ou null se não houver sugestão.",
            },
        },
        "required": ["draft", "justification"],
    },
}


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def extract_tool_response(response) -> tuple[str, str, str | None]:
    """Extract draft, justification and suggested_attachment from tool_use response."""
    for block in response.content:
        if block.type == "tool_use" and block.name == DRAFT_TOOL_NAME:
            inp = block.input
            suggested = inp.get("suggested_attachment") or None
            return inp.get("draft", ""), inp.get("justification", ""), suggested
    # Fallback: try to extract text if no tool_use block
    for block in response.content:
        if hasattr(block, "text"):
            return block.text.strip(), "Resposta não usou tool_use", None
    return "", "Sem resposta", None


def validate_suggested_attachment(suggested: str | None) -> str | None:
    if not suggested:
        return None
    file_path = ATTACHMENTS_DIR / suggested
    if file_path.exists() and file_path.is_file():
        return suggested
    return None


async def call_haiku(
    user_content: str,
    approach_modifier: str,
    system_prompt: str,
    rules_section: str = "",
    knowledge_section: str = "",
) -> tuple[str, str, str | None]:
    system = [
        {
            "type": "text",
            "text": system_prompt + rules_section + knowledge_section,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"\n\n## Estilo desta variação\n{approach_modifier}",
        },
    ]
    client = get_anthropic_client()
    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=1024,
        system=system,
        tools=[DRAFT_TOOL],
        tool_choice={"type": "tool", "name": DRAFT_TOOL_NAME},
        messages=[{"role": "user", "content": user_content}],
    )
    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    logger.info(
        "Cache metrics: read=%d write=%d input=%d",
        cache_read,
        cache_write,
        usage.input_tokens,
    )
    draft_text, justification, suggested = extract_tool_response(response)
    suggested = validate_suggested_attachment(suggested)
    return draft_text, justification, suggested
