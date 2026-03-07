import asyncio
import json
import logging
from datetime import datetime

import anthropic

from app.config import settings
from app.database import get_db
from app.services.conversation_analysis import analyze_conversation

logger = logging.getLogger(__name__)

DIGEST_SYSTEM_PROMPT = """Você é um analista de vendas interno gerando um relatório de desempenho de operador.

Este relatório é INTERNO, só o gestor vê. Seja direto e sem eufemismo.
"Piloto automático", "resposta preguiçosa", "perdeu a venda" são termos aceitáveis.

Você vai receber:
1. Todas as análises individuais de conversas deste operador no período
2. Métricas agregadas

Seu trabalho:
- Identificar PADRÕES de comportamento (não repetir cada conversa)
- Para cada padrão, dar EXEMPLOS CONCRETOS de conversas específicas
- Listar vendas que podem ser salvas com intervenção direta do gestor
- Ser específico nas sugestões de melhoria

Responda APENAS com JSON válido, sem markdown."""

DIGEST_USER_TEMPLATE = """## Operador: {operator_name}

## Métricas agregadas

{aggregated_metrics}

## Análises individuais de conversas

{assessments_text}

Retorne um JSON com esta estrutura:
{{
  "summary": "2-3 frases diretas sobre o desempenho geral deste operador no período",
  "patterns": [
    {{
      "pattern": "descrição do padrão identificado",
      "examples": ["Conv com João (#12): detalhe concreto", "Conv com Maria (#8): detalhe concreto"],
      "suggestion": "sugestão específica de melhoria"
    }}
  ],
  "factual_issues_highlight": [
    {{
      "conversation_id": 12,
      "contact_name": "João",
      "issue": "descrição do erro factual"
    }}
  ],
  "salvageable_sales": [
    {{
      "conversation_id": 12,
      "contact_name": "João",
      "situation": "contexto breve",
      "suggestion": "como retomar",
      "priority": "high/medium"
    }}
  ]
}}"""


async def run_analysis(period_start: str, period_end: str) -> int:
    """Run full analysis for a period. Returns the analysis_run id."""
    db = await get_db()
    try:
        # Create run record
        cursor = await db.execute(
            "INSERT INTO analysis_runs (period_start, period_end, status) VALUES (?, ?, 'running')",
            (period_start, period_end),
        )
        run_id = cursor.lastrowid
        await db.commit()

        try:
            await _process_analysis(db, run_id, period_start, period_end)
        except Exception as e:
            logger.exception("Analysis run %d failed", run_id)
            await db.execute(
                "UPDATE analysis_runs SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), run_id),
            )
            await db.commit()

        return run_id
    finally:
        await db.close()


async def _process_analysis(db, run_id: int, period_start: str, period_end: str):
    """Core analysis processing."""

    # Find conversations with outbound activity in period
    rows = await db.execute(
        """SELECT DISTINCT c.id, c.contact_name
           FROM conversations c
           JOIN messages m ON m.conversation_id = c.id
           WHERE m.direction = 'outbound'
             AND m.created_at >= ? AND m.created_at <= ?""",
        (period_start, period_end + " 23:59:59"),
    )
    active_conversations = await rows.fetchall()

    # Find unanswered conversations (inbound in period but no outbound)
    rows = await db.execute(
        """SELECT c.id, c.contact_name,
                  (SELECT content FROM messages WHERE conversation_id = c.id AND direction = 'inbound' ORDER BY created_at DESC LIMIT 1) as last_inbound_message,
                  (SELECT created_at FROM messages WHERE conversation_id = c.id AND direction = 'inbound' ORDER BY created_at DESC LIMIT 1) as last_inbound_at
           FROM conversations c
           WHERE EXISTS (
               SELECT 1 FROM messages m WHERE m.conversation_id = c.id
               AND m.direction = 'inbound' AND m.created_at >= ? AND m.created_at <= ?
           )
           AND NOT EXISTS (
               SELECT 1 FROM messages m WHERE m.conversation_id = c.id
               AND m.direction = 'outbound' AND m.created_at >= ? AND m.created_at <= ?
           )""",
        (period_start, period_end + " 23:59:59", period_start, period_end + " 23:59:59"),
    )
    unanswered = [dict(r) for r in await rows.fetchall()]

    # For each active conversation, find operators who sent messages in period
    conv_operator_pairs = []
    for conv in active_conversations:
        rows = await db.execute(
            """SELECT DISTINCT sent_by FROM messages
               WHERE conversation_id = ? AND direction = 'outbound' AND sent_by IS NOT NULL
               AND created_at >= ? AND created_at <= ?""",
            (conv["id"], period_start, period_end + " 23:59:59"),
        )
        operators = await rows.fetchall()
        for op in operators:
            conv_operator_pairs.append((conv["id"], op["sent_by"]))

    total_conversations = len(active_conversations)
    operators_set = set(op for _, op in conv_operator_pairs)
    total_operators = len(operators_set)

    # Process conversations with concurrency limit
    semaphore = asyncio.Semaphore(5)
    assessments = []

    async def process_one(conv_id, operator_name):
        async with semaphore:
            try:
                return await analyze_conversation(db, conv_id, operator_name, period_start, period_end)
            except Exception:
                logger.exception("Failed to analyze conversation %d for operator %s", conv_id, operator_name)
                return None

    tasks = [process_one(conv_id, op_name) for conv_id, op_name in conv_operator_pairs]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result is not None:
            assessments.append(result)

    # Save assessments
    for assessment in assessments:
        await db.execute(
            """INSERT INTO conversation_assessments
               (analysis_run_id, conversation_id, operator_name, engagement_level,
                sale_status, recovery_potential, recovery_suggestion,
                factual_issues_json, overall_assessment, metrics_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                assessment["conversation_id"],
                assessment["operator_name"],
                assessment.get("engagement_level"),
                assessment.get("sale_status"),
                assessment.get("recovery_potential"),
                assessment.get("recovery_suggestion"),
                json.dumps(assessment.get("factual_issues", []), ensure_ascii=False),
                assessment.get("overall_assessment"),
                json.dumps(assessment.get("metrics", {}), ensure_ascii=False),
            ),
        )
    await db.commit()

    # Generate operator digests
    for operator_name in operators_set:
        op_assessments = [a for a in assessments if a["operator_name"] == operator_name]
        try:
            digest = await _generate_operator_digest(operator_name, op_assessments)
            await db.execute(
                """INSERT INTO operator_digests
                   (analysis_run_id, operator_name, summary, patterns_json,
                    factual_issues_json, salvageable_sales_json, metrics_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    operator_name,
                    digest.get("summary"),
                    json.dumps(digest.get("patterns", []), ensure_ascii=False),
                    json.dumps(digest.get("factual_issues_highlight", []), ensure_ascii=False),
                    json.dumps(digest.get("salvageable_sales", []), ensure_ascii=False),
                    json.dumps(_aggregate_metrics(op_assessments), ensure_ascii=False),
                ),
            )
        except Exception:
            logger.exception("Failed to generate digest for operator %s", operator_name)
    await db.commit()

    # Save unanswered as JSON in a special operator_digest entry
    if unanswered:
        await db.execute(
            """INSERT INTO operator_digests
               (analysis_run_id, operator_name, summary, salvageable_sales_json)
               VALUES (?, ?, ?, ?)""",
            (
                run_id,
                "__unanswered__",
                f"{len(unanswered)} conversas sem resposta no período",
                json.dumps(unanswered, ensure_ascii=False),
            ),
        )
        await db.commit()

    # Update run status
    await db.execute(
        """UPDATE analysis_runs
           SET status = 'completed', total_conversations = ?, total_operators = ?,
               completed_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (total_conversations, total_operators, run_id),
    )
    await db.commit()


def _aggregate_metrics(assessments: list[dict]) -> dict:
    """Aggregate metrics across assessments for one operator."""
    total_messages = sum(a.get("metrics", {}).get("total_messages", 0) for a in assessments)
    total_conversations = len(assessments)

    all_rates = [a["metrics"]["draft_acceptance_rate"] for a in assessments
                 if a.get("metrics", {}).get("draft_acceptance_rate") is not None]
    avg_acceptance_rate = sum(all_rates) / len(all_rates) if all_rates else None

    status_counts = {}
    for a in assessments:
        status = a.get("sale_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    factual_issues_count = sum(len(a.get("factual_issues", [])) for a in assessments)

    return {
        "total_messages": total_messages,
        "total_conversations": total_conversations,
        "avg_draft_acceptance_rate": avg_acceptance_rate,
        "sale_status_distribution": status_counts,
        "factual_issues_count": factual_issues_count,
    }


async def _generate_operator_digest(operator_name: str, assessments: list[dict]) -> dict:
    """Generate operator digest via Sonnet."""
    metrics = _aggregate_metrics(assessments)

    # Build aggregated metrics text
    metrics_lines = [
        f"Total de conversas: {metrics['total_conversations']}",
        f"Total de mensagens enviadas: {metrics['total_messages']}",
    ]
    if metrics["avg_draft_acceptance_rate"] is not None:
        metrics_lines.append(f"Taxa média de aceitação sem edição: {metrics['avg_draft_acceptance_rate']:.0f}%")
    metrics_lines.append(f"Distribuição de status: {json.dumps(metrics['sale_status_distribution'], ensure_ascii=False)}")
    metrics_lines.append(f"Erros factuais encontrados: {metrics['factual_issues_count']}")
    aggregated_metrics = "\n".join(metrics_lines)

    # Build assessments text
    assessment_parts = []
    for a in assessments:
        contact = a.get("contact_name", "?")
        conv_id = a.get("conversation_id", "?")
        part = f"### Conv com {contact} (#{conv_id})\n"
        part += f"Engajamento: {a.get('engagement_level', '?')}\n"
        part += f"Status venda: {a.get('sale_status', '?')}\n"
        part += f"Potencial recuperação: {a.get('recovery_potential', '?')}\n"
        if a.get("recovery_suggestion"):
            part += f"Sugestão: {a['recovery_suggestion']}\n"
        part += f"Avaliação: {a.get('overall_assessment', '?')}\n"
        m = a.get("metrics", {})
        if m.get("draft_acceptance_rate") is not None:
            part += f"Aceitação sem edição: {m['draft_acceptance_rate']:.0f}%\n"
        issues = a.get("factual_issues", [])
        if issues:
            part += f"Erros factuais: {json.dumps(issues, ensure_ascii=False)}\n"
        assessment_parts.append(part)
    assessments_text = "\n".join(assessment_parts)

    user_content = DIGEST_USER_TEMPLATE.format(
        operator_name=operator_name,
        aggregated_metrics=aggregated_metrics,
        assessments_text=assessments_text,
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=DIGEST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    response_text = response.content[0].text.strip()

    try:
        digest = json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                digest = json.loads(response_text[start:end])
            except json.JSONDecodeError:
                digest = {
                    "summary": response_text,
                    "patterns": [],
                    "factual_issues_highlight": [],
                    "salvageable_sales": [],
                }
        else:
            digest = {
                "summary": response_text,
                "patterns": [],
                "factual_issues_highlight": [],
                "salvageable_sales": [],
            }

    return digest
