import json
import logging
from datetime import datetime

from app.config import settings
from app.services.claude_client import get_anthropic_client
from app.services.knowledge import load_knowledge_base

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """Você é um analista de vendas interno. Seu trabalho é avaliar a qualidade de uma conversa de WhatsApp entre operador e cliente.

Este relatório é INTERNO, só o gestor vê. Seja direto. Nomeie problemas sem eufemismo. "Piloto automático", "resposta preguiçosa", "perdeu a venda" são termos aceitáveis quando adequados.

Você vai receber:
1. A conversa completa (mensagens do cliente e do operador)
2. Dados sobre o uso do copiloto de IA (se o operador editou os drafts ou aceitou sem mudar)
3. A base de conhecimento dos cursos (para verificar erros factuais)
4. Métricas quantitativas do operador nesta conversa

Sua tarefa é avaliar:

## Erros factuais
Compare o que o operador disse com a base de conhecimento. Só flagge CONTRADIÇÕES DIRETAS (operador disse X, base diz Y). Se o operador disse algo que a base não cobre, NÃO é erro.

## Engajamento
Avalie se o operador personalizou as respostas ou foi no piloto automático:
- "high": referencia contexto do cliente, demonstra interesse genuíno, avança a conversa
- "medium": funcional mas genérico, poderia ser pra qualquer cliente
- "low": seco, curto, sem personalização, não avança a conversa

Se o operador aceitou TODOS os drafts sem editar nenhum, o engajamento é no MÁXIMO "medium", independente da qualidade do draft. Aceitar tudo sem revisar indica falta de julgamento.

## Status da venda
- "active": cliente engajado e respondendo
- "cooling": cliente parou de responder ou disse "vou pensar" sem follow-up
- "dead": cliente recusou explicitamente ou sem resposta há 3+ dias
- "converted": venda concluída

## Potencial de recuperação (só para cooling/dead)
- "high": cliente tinha interesse concreto, problema é tratável
- "medium": interesse existia mas fraco
- "low": pouco a fazer
- "none": cliente recusou definitivamente ou nunca teve interesse real

Responda APENAS com um JSON válido, sem markdown, sem texto fora do JSON."""

ANALYSIS_USER_TEMPLATE = """## Base de conhecimento dos cursos

{knowledge_base}

## Métricas do operador nesta conversa

{metrics_text}

## Dados do copiloto (edit_pairs)

{edit_pairs_text}

## Conversa completa

{conversation_text}

Retorne um JSON com esta estrutura exata:
{{
  "factual_issues": [
    {{"message_excerpt": "trecho da msg do operador", "claim": "o que disse", "knowledge_says": "o que a base diz", "severity": "high ou medium"}}
  ],
  "engagement_level": "high/medium/low",
  "engagement_notes": "explicação direta do por quê",
  "sale_status": "active/cooling/dead/converted",
  "recovery_potential": "high/medium/low/none",
  "recovery_suggestion": "sugestão concreta de como retomar, ou null",
  "overall_assessment": "2-3 frases diretas sobre a condução desta conversa"
}}"""


async def analyze_conversation(
    db,
    conversation_id: int,
    operator_name: str,
    period_start: str,
    period_end: str,
) -> dict:
    """Analyze a single conversation for one operator. Returns structured assessment."""

    # Fetch conversation info
    row = await db.execute(
        "SELECT contact_name, funnel_product, funnel_stage FROM conversations WHERE id = ?",
        (conversation_id,),
    )
    conv = await row.fetchone()
    contact_name = conv["contact_name"] if conv else "Desconhecido"

    # Fetch all messages (full history for context)
    rows = await db.execute(
        "SELECT direction, content, sent_by, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    messages = await rows.fetchall()

    # Build conversation text
    conv_lines = []
    for msg in messages:
        sender = msg["sent_by"] or ("Cliente" if msg["direction"] == "inbound" else "Operador")
        if msg["direction"] == "inbound":
            sender = "Cliente"
        ts = msg["created_at"]
        conv_lines.append(f"[{ts}] {sender}: {msg['content']}")
    conversation_text = "\n".join(conv_lines)

    # Fetch edit_pairs for this conversation by this operator
    # We match via messages.sent_by to find which edit_pairs belong to this operator
    rows = await db.execute(
        """SELECT ep.customer_message, ep.original_draft, ep.final_message,
                  ep.was_edited, ep.strategic_annotation, ep.selected_draft_index,
                  ep.regeneration_count, ep.attachment_filename, ep.situation_summary,
                  ep.created_at
           FROM edit_pairs ep
           WHERE ep.conversation_id = ?
           ORDER BY ep.created_at ASC""",
        (conversation_id,),
    )
    edit_pairs = await rows.fetchall()

    # Compute metrics
    operator_messages = [m for m in messages if m["direction"] == "outbound" and m["sent_by"] == operator_name]
    total_messages = len(operator_messages)

    total_edit_pairs = len(edit_pairs)
    accepted_without_edit = sum(1 for ep in edit_pairs if not ep["was_edited"])
    draft_acceptance_rate = (accepted_without_edit / total_edit_pairs * 100) if total_edit_pairs > 0 else None
    avg_regeneration = sum(ep["regeneration_count"] or 0 for ep in edit_pairs) / total_edit_pairs if total_edit_pairs > 0 else 0

    # Response times: time between inbound and next outbound by this operator
    response_times = []
    for i, msg in enumerate(messages):
        if msg["direction"] == "inbound":
            # Find next outbound by this operator
            for j in range(i + 1, len(messages)):
                if messages[j]["direction"] == "outbound" and messages[j]["sent_by"] == operator_name:
                    try:
                        t_in = datetime.fromisoformat(msg["created_at"])
                        t_out = datetime.fromisoformat(messages[j]["created_at"])
                        delta_min = (t_out - t_in).total_seconds() / 60
                        response_times.append(delta_min)
                    except (ValueError, TypeError):
                        pass
                    break

    # Approach distribution
    approach_counts = {}
    for ep in edit_pairs:
        idx = ep["selected_draft_index"]
        if idx is not None:
            approaches = ["direta", "consultiva", "casual"]
            approach = approaches[idx] if idx < len(approaches) else f"index_{idx}"
            approach_counts[approach] = approach_counts.get(approach, 0) + 1

    # Build metrics text
    metrics_parts = [
        f"Operador: {operator_name}",
        f"Mensagens enviadas: {total_messages}",
    ]
    if draft_acceptance_rate is not None:
        metrics_parts.append(f"Taxa de aceitação sem edição: {draft_acceptance_rate:.0f}% ({accepted_without_edit}/{total_edit_pairs})")
    else:
        metrics_parts.append("Sem dados de draft (operador pode ter digitado direto)")
    metrics_parts.append(f"Regenerações médias: {avg_regeneration:.1f}")
    if response_times:
        median_rt = sorted(response_times)[len(response_times) // 2]
        max_rt = max(response_times)
        metrics_parts.append(f"Tempo de resposta: mediana {median_rt:.0f}min, máximo {max_rt:.0f}min")
    if approach_counts:
        dist = ", ".join(f"{k}: {v}" for k, v in approach_counts.items())
        metrics_parts.append(f"Approaches escolhidos: {dist}")
    if conv and conv["funnel_product"]:
        metrics_parts.append(f"Produto: {conv['funnel_product']}")
    if conv and conv["funnel_stage"]:
        metrics_parts.append(f"Estágio funil: {conv['funnel_stage']}")

    metrics_text = "\n".join(metrics_parts)

    # Build edit_pairs text
    if edit_pairs:
        ep_parts = []
        for ep in edit_pairs:
            ep_text = f"Cliente: {ep['customer_message']}\n"
            ep_text += f"Draft IA: {ep['original_draft']}\n"
            ep_text += f"Operador enviou: {ep['final_message']}\n"
            ep_text += f"Editou: {'sim' if ep['was_edited'] else 'não'}"
            if ep["strategic_annotation"]:
                ep_text += f"\nAnotação estratégica: {ep['strategic_annotation']}"
            if ep["attachment_filename"]:
                ep_text += f"\nAnexo: {ep['attachment_filename']}"
            ep_parts.append(ep_text)
        edit_pairs_text = "\n\n---\n\n".join(ep_parts)
    else:
        edit_pairs_text = "Sem dados de edit_pairs para esta conversa (operador pode ter digitado mensagens diretamente)."

    # Load knowledge base
    knowledge_base = load_knowledge_base()

    # Build prompt
    user_content = ANALYSIS_USER_TEMPLATE.format(
        knowledge_base=knowledge_base or "(base de conhecimento vazia)",
        metrics_text=metrics_text,
        edit_pairs_text=edit_pairs_text,
        conversation_text=conversation_text,
    )

    # Call Haiku
    client = get_anthropic_client()
    response = await client.messages.create(
        model=settings.claude_haiku_model,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": ANALYSIS_SYSTEM_PROMPT,
            },
            {
                "type": "text",
                "text": f"\n\n## Base de conhecimento\n\n{knowledge_base or '(vazia)'}",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    response_text = response.content[0].text.strip()

    # Parse JSON response
    try:
        assessment = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                assessment = json.loads(response_text[start:end])
            except json.JSONDecodeError:
                logger.warning("Failed to parse assessment JSON for conversation %d", conversation_id)
                assessment = {
                    "factual_issues": [],
                    "engagement_level": "medium",
                    "engagement_notes": "Falha ao processar análise",
                    "sale_status": "active",
                    "recovery_potential": "none",
                    "recovery_suggestion": None,
                    "overall_assessment": response_text,
                }
        else:
            assessment = {
                "factual_issues": [],
                "engagement_level": "medium",
                "engagement_notes": "Falha ao processar análise",
                "sale_status": "active",
                "recovery_potential": "none",
                "recovery_suggestion": None,
                "overall_assessment": response_text,
            }

    # Add metadata
    assessment["conversation_id"] = conversation_id
    assessment["operator_name"] = operator_name
    assessment["contact_name"] = contact_name
    assessment["metrics"] = {
        "total_messages": total_messages,
        "draft_acceptance_rate": draft_acceptance_rate,
        "avg_regeneration": avg_regeneration,
        "response_times": response_times,
        "approach_counts": approach_counts,
    }

    return assessment
