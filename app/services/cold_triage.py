"""Cold rewarm triagem: classifica objeção, decide ação, compõe mensagem no tom Caio.

Pipeline manual acionado via botão:
  select_cold_candidates → classify_conversation (Haiku) → apply_matrix →
  compose_message (Haiku) → grava cold_dispatches como 'previewed' →
  modal de revisão → execute_batch com rate limit.
"""

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import now_local, settings
from app.database import get_db
from app.services.claude_client import get_anthropic_client
from app.services.message_sender import send_and_record

logger = logging.getLogger(__name__)

COLD_PRODUCT = "curso-cdo"
COLD_COOLDOWN_DAYS = 90
COLD_FRESH_DAYS_MIN = 30  # última mensagem inbound tem que ser mais antiga que isso
PREVIEW_LIMIT = 20
CANDIDATE_POOL = 80  # seleciona até N antes de classificar e reordenar

# Classificação
CLASSIFICATIONS = (
    "abandono_checkout",   # lead pediu link explicitamente, recebeu, sumiu (intenção verbal máxima)
    "objecao_preco",
    "objecao_timing",
    "objecao_conteudo",
    "tire_kicker",
    "negativo_explicito",
    "perdido_no_ruido",
    "nao_classificavel",
)

# Estágio que o lead efetivamente atingiu (inferido do histórico, independente
# do funnel_stage atual da tabela conversations que é mutável).
STAGES_REACHED = (
    "link_sent",           # operador enviou URL de checkout ou referência explícita ao link
    "handbook_sent",       # operador enviou handbook/material mas não chegou ao link
    "only_qualifying",     # lead qualificou (perguntou algo) mas não recebeu handbook nem link
    "nunca_qualificou",    # lead mal engajou, praticamente não houve conversa
)

COLD_CLASSIFY_TOOL_NAME = "cold_classify"
COLD_CLASSIFY_TOOL = {
    "name": COLD_CLASSIFY_TOOL_NAME,
    "description": "Classifica a objeção implícita de saída do lead e identifica até onde o funil avançou.",
    "input_schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": list(CLASSIFICATIONS),
                "description": (
                    "abandono_checkout: lead VERBALIZOU pedido do link de pagamento ('me da o link', 'manda o link', 'onde pago', 'como faço pra comprar') APÓS saber o preço ou engajar no conteúdo, recebeu o link e silenciou. Intenção de compra verbal máxima. "
                    "objecao_preco: reagiu a preço ou mencionou valor, depois sumiu, SEM ter chegado a pedir o link. "
                    "objecao_timing: disse que volta depois. "
                    "objecao_conteudo: dúvida específica sobre conteúdo não resolvida. "
                    "tire_kicker: pediu handbook sem engajar. NUNCA se aplica se o operador chegou a enviar link de pagamento ao lead. "
                    "negativo_explicito: pediu pra parar ou foi hostil. "
                    "perdido_no_ruido: silenciou sem sinal claro. "
                    "nao_classificavel: nada acima cabe."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "med", "low"],
                "description": "Confiança na classificação. Na dúvida real, use low.",
            },
            "stage_reached": {
                "type": "string",
                "enum": list(STAGES_REACHED),
                "description": (
                    "Até onde o lead avançou no funil, inferido do histórico outbound real. "
                    "link_sent: operador enviou URL de pagamento/checkout do curso CDO (hotmart, eduzz, kiwify, pay, stripe etc), "
                    "OU mencionou explicitamente 'segue o link', 'link de compra', 'link de pagamento' de forma clara. "
                    "handbook_sent: operador enviou material/handbook/PDF mas NÃO chegou a enviar o link de pagamento. "
                    "only_qualifying: lead trocou mensagens qualificando interesse mas nenhum material foi enviado. "
                    "nunca_qualificou: lead praticamente não engajou, sem conversa significativa."
                ),
            },
            "quote_from_lead": {
                "type": "string",
                "description": "Trecho literal da última mensagem relevante do lead que sustenta a classificação. Vazio se não há trecho claro.",
            },
            "reasoning": {
                "type": "string",
                "description": "1-2 frases justificando a classificação e o stage_reached.",
            },
        },
        "required": ["classification", "confidence", "stage_reached", "quote_from_lead", "reasoning"],
    },
}

COLD_CLASSIFY_SYSTEM_PROMPT = """Você classifica conversas de leads do curso CDO que ficaram frias (+30 dias sem mensagem).

Duas inferências por conversa:
1. A objeção de saída do lead (classification).
2. Até onde o lead avançou no funil (stage_reached), baseado no histórico outbound real.

## Classificações de objeção (classification)

- objecao_preco: lead reagiu mal ao preço, disse "caro", "salgado", "não cabe", ou sumiu exatamente depois de ver o valor.
- objecao_timing: lead disse explicitamente que volta depois. Exemplos: "mês que vem volto", "depois do [evento]", "quando receber", "tô viajando e retomo", "em [mês futuro]".
- objecao_conteudo: lead perguntou algo específico sobre conteúdo/escopo e não teve resposta satisfatória, ou dúvida ficou pendente.
- tire_kicker: lead pediu handbook ou link, nunca respondeu de volta, sumiu imediato. Sem engajamento real em momento algum.
- negativo_explicito: lead pediu pra parar ("para de mandar", "não tenho interesse", "tira meu número"), foi hostil, ou sinalizou claramente desistência.
- perdido_no_ruido: silenciou sem sinal claro. Pode ter esquecido, pode ter comprado outro, não dá pra saber.
- nao_classificavel: histórico muito curto ou ambíguo pra qualquer das acima.

## Estágio atingido (stage_reached)

Detecte pelas mensagens OUTBOUND (do operador) no histórico. Ordem de precedência (tome o mais avançado que tiver evidência):

- link_sent: a conversa tem mensagem outbound com URL de checkout/pagamento do curso CDO (hotmart, eduzz, kiwify, pay, stripe, checkout.*, compra.*), OU uma frase explícita do operador tipo "segue o link", "link de pagamento", "link pra comprar". Se chegou aqui, marque link_sent, mesmo que handbook também tenha sido enviado.

- handbook_sent: a conversa tem mensagem outbound com anexo/referência ao handbook ou material (PDF do curso, menção a "handbook", "material completo", envio de documento explicativo), MAS não chegou a enviar o link de pagamento.

- only_qualifying: não há evidência de envio de handbook nem link. O lead engajou em conversa qualificadora (perguntou sobre o curso, o operador respondeu dúvidas) mas o funil não avançou.

- nunca_qualificou: conversa praticamente vazia. Lead mandou 1-2 mensagens genéricas e sumiu. Ou só inbound sem respostas significativas.

## Diretrizes

- Seja conservador na classificação de objeção. Na dúvida, use confidence=low.
- No stage_reached, seja afirmativo. É inferência sobre fatos observáveis no outbound, não sobre intenção. Se viu o link na outbound, é link_sent.
- Se houver qualquer hostilidade ou pedido explícito de parar, use negativo_explicito com confidence=high.
- O quote_from_lead deve ser uma frase literal do lead, sem paráfrase.
- Retorne sempre via tool cold_classify."""


# Compositor
COLD_COMPOSE_TOOL_NAME = "cold_compose_message"
COLD_COMPOSE_TOOL = {
    "name": COLD_COMPOSE_TOOL_NAME,
    "description": "Compõe a mensagem de recuperação no tom Caio digitando.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Texto final a ser enviado ao lead, já no tom Caio.",
            },
        },
        "required": ["message"],
    },
}

COLD_COMPOSE_SYSTEM_PROMPT = """Você escreve mensagens de recuperação de leads frios (+30 dias sem conversa) em nome do Caio Gomes, no WhatsApp.

Regra número um: a mensagem tem que parecer que o Caio digitou do celular. Não sistema, não bot, não copywriter. Ele.

Tom:
- minúsculas dominantes. nome próprio pode vir com maiúscula se soar natural, mas início de frase é minúsculo. nada de títulos.
- primeira pessoa, direto. "oi", "lembrei de você", "to mandando", "abri".
- zero em-dash. zero travessão. zero "—".
- sem pontos de exclamação acumulados, sem emoji gratuito (no máximo um, raramente).
- frases curtas, às vezes incompletas. pontuação relaxada.
- cita literalmente o que o lead disse antes, com marcador temporal vago ("você me falou em julho...", "lá em agosto você comentou que..."). Use o quote fornecido.
- menciona a oferta de forma clara mas sem venda agressiva. Abrir janela: "abri algumas vagas", "consegui abrir uma sessão", "to liberando".
- em cerca de 1 em cada 4 ou 5 mensagens, inclua um pequeno fat-finger: letra trocada, acento omitido, palavra levemente errada. exemplos: "obirgado" no lugar de "obrigado", "vc" alternando com "você", "tava", "meu", "paciencia" sem acento. Não force. Sutil.
- não tente fazer piada. seriedade amigável.
- tamanho ideal: 3 a 6 linhas, como mensagem de WhatsApp real.

Estrutura livre, mas geralmente:
1. abertura curta ("oi [nome], caio aqui" ou "[nome], lembrei de você")
2. menção específica ao que o lead disse antes (com a citação ou paráfrase próxima)
3. a oferta ou o conteúdo novo (mentoria ou post), sem pressão
4. convite aberto pra resposta ("se ainda faz sentido, me manda um oi")
5. fechamento minimalista ("abraço", "abç", "valeu")

Ações possíveis (você recebe qual é no prompt):
- mentoria: ofereça uma sessão privada de 1h com o Caio. Tem poucas vagas. Use prazo curto de forma natural (não "promoção relâmpago"). Exemplo: "consegui abrir 3 sessões individuais esse mês".
- conteudo: mencione que publicou uma série recente sobre atribuição em marketing (link será incluído pelo operador, deixe placeholder [link] na mensagem se precisar).

Retorne sempre via tool cold_compose_message com o campo message."""


# ───────────────────────── Seleção ─────────────────────────

async def select_cold_candidates(db, limit: int = CANDIDATE_POOL) -> list[dict[str, Any]]:
    """Seleciona até `limit` conversas elegíveis ao cold rewarm.

    Filtros:
      - funnel_product = curso-cdo
      - última mensagem inbound > 30 dias atrás
      - cold_do_not_contact = 0
      - sem cold_dispatch criado nos últimos 90 dias

    O estágio no funil NÃO é filtro aqui: `funnel_stage` em `conversations` é sobrescrito
    periodicamente pelo `situation_summary` do Haiku, o que descarta leads que passaram
    por handbook/link mas tiveram stage reclassificado depois. O stage real é inferido
    do histórico pelo classificador (stage_reached), que decide depois se é tire_kicker
    ou vale toque.

    Ordena por frescor (menor dias frio antes) dentro do pool.
    """
    cursor = await db.execute(
        """
        WITH last_inbound AS (
            SELECT conversation_id, MAX(created_at) AS last_at
            FROM messages
            WHERE direction = 'inbound'
            GROUP BY conversation_id
        ),
        recent_cold AS (
            SELECT conversation_id, MAX(created_at) AS last_cold_at
            FROM cold_dispatches
            GROUP BY conversation_id
        )
        SELECT c.id, c.phone_number, c.contact_name, c.funnel_stage,
               li.last_at AS last_inbound_at,
               julianday('now') - julianday(li.last_at) AS days_cold
        FROM conversations c
        JOIN last_inbound li ON li.conversation_id = c.id
        LEFT JOIN recent_cold rc ON rc.conversation_id = c.id
        WHERE c.funnel_product = ?
          AND COALESCE(c.cold_do_not_contact, 0) = 0
          AND julianday('now') - julianday(li.last_at) >= ?
          AND (rc.last_cold_at IS NULL
               OR julianday('now') - julianday(rc.last_cold_at) >= ?)
        ORDER BY days_cold ASC
        LIMIT ?
        """,
        (
            COLD_PRODUCT,
            COLD_FRESH_DAYS_MIN,
            COLD_COOLDOWN_DAYS,
            limit,
        ),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ───────────────────────── Classificação ─────────────────────────

async def _load_history_for_classify(db, conversation_id: int) -> str:
    cursor = await db.execute(
        """SELECT direction, content, sent_by, created_at
           FROM messages WHERE conversation_id = ?
           ORDER BY created_at ASC, id ASC""",
        (conversation_id,),
    )
    rows = await cursor.fetchall()
    if not rows:
        return "(conversa vazia)"
    lines = []
    for m in rows:
        tag = "cliente" if m["direction"] == "inbound" else f"operador ({m['sent_by'] or 'equipe'})"
        lines.append(f"[{m['created_at']}] {tag}: {m['content']}")
    return "\n".join(lines)


def _parse_classify_response(response) -> dict[str, Any]:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == COLD_CLASSIFY_TOOL_NAME:
            inp = block.input or {}
            classification = inp.get("classification", "nao_classificavel")
            if classification not in CLASSIFICATIONS:
                classification = "nao_classificavel"
            confidence = inp.get("confidence", "low")
            if confidence not in ("high", "med", "low"):
                confidence = "low"
            stage_reached = inp.get("stage_reached", "nunca_qualificou")
            if stage_reached not in STAGES_REACHED:
                stage_reached = "nunca_qualificou"
            return {
                "classification": classification,
                "confidence": confidence,
                "stage_reached": stage_reached,
                "quote_from_lead": (inp.get("quote_from_lead") or "").strip(),
                "reasoning": (inp.get("reasoning") or "").strip(),
            }
    return {
        "classification": "nao_classificavel",
        "confidence": "low",
        "stage_reached": "nunca_qualificou",
        "quote_from_lead": "",
        "reasoning": "sem tool_use na resposta",
    }


async def classify_conversation(conversation_id: int, db=None) -> dict[str, Any]:
    """Classifica a conversa via Haiku. Retorna dict normalizado."""
    own = db is None
    if own:
        db = await get_db()
    try:
        history_text = await _load_history_for_classify(db, conversation_id)
    finally:
        if own:
            await db.close()

    try:
        client = get_anthropic_client()
        response = await client.messages.create(
            model=settings.claude_haiku_model,
            max_tokens=512,
            system=COLD_CLASSIFY_SYSTEM_PROMPT,
            tools=[COLD_CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": COLD_CLASSIFY_TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Classifique a objeção de saída do lead nesta conversa:\n\n"
                        f"{history_text}"
                    ),
                }
            ],
        )
        return _parse_classify_response(response)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cold classify failed conv=%s: %s", conversation_id, exc)
        return {
            "classification": "nao_classificavel",
            "confidence": "low",
            "stage_reached": "nunca_qualificou",
            "quote_from_lead": "",
            "reasoning": f"erro: {exc}",
        }


# ───────────────────────── Matriz ─────────────────────────

# Ação por classificação × stage_reached, quando confiança >= med e cap não atingido.
# Filosofia: link_sent é sagrado. Quem chegou lá, exceto hostilidade explícita, vira mentoria
# porque o sinal de intenção é forte demais pra ignorar.
_MATRIX_FULL = {
    "abandono_checkout": {
        "link_sent":        "mentoria",   # caso de maior valor do pool
        "handbook_sent":    "mentoria",   # raro mas pode ocorrer se Haiku inferir pedido de link via conversa
        "only_qualifying":  "conteudo",
        "nunca_qualificou": "skip",
    },
    "objecao_preco": {
        "link_sent":        "mentoria",
        "handbook_sent":    "skip",
        "only_qualifying":  "skip",
        "nunca_qualificou": "skip",
    },
    "objecao_timing": {
        "link_sent":        "mentoria",
        "handbook_sent":    "mentoria",
        "only_qualifying":  "conteudo",
        "nunca_qualificou": "skip",
    },
    "objecao_conteudo": {
        "link_sent":        "mentoria",
        "handbook_sent":    "conteudo",
        "only_qualifying":  "conteudo",
        "nunca_qualificou": "skip",
    },
    "tire_kicker": {
        "link_sent":        "mentoria",   # fallback: Haiku errou a classificação (proibido pelo prompt,
                                           # mas se vier, a matriz rebate pra mentoria; é lead com link,
                                           # merece a oferta)
        "handbook_sent":    "skip",
        "only_qualifying":  "skip",
        "nunca_qualificou": "skip",
    },
    "negativo_explicito": {
        "link_sent":        "skip",       # hostilidade explícita nunca vira toque, nem pra link
        "handbook_sent":    "skip",
        "only_qualifying":  "skip",
        "nunca_qualificou": "skip",
    },
    "perdido_no_ruido": {
        "link_sent":        "mentoria",   # rede de segurança: silêncio pós-link é valioso
        "handbook_sent":    "skip",
        "only_qualifying":  "skip",
        "nunca_qualificou": "skip",
    },
    "nao_classificavel": {
        "link_sent":        "mentoria",   # rede de segurança: Haiku indeciso + link = ainda vale toque
        "handbook_sent":    "skip",
        "only_qualifying":  "skip",
        "nunca_qualificou": "skip",
    },
}

# Quando cap de mentoria atingido: mentoria rebaixa pra conteudo se stage é link/handbook,
# senão vira skip.
_DEMOTE_WHEN_CAP = {
    "link_sent":        "conteudo",
    "handbook_sent":    "conteudo",
    "only_qualifying":  "skip",
    "nunca_qualificou": "skip",
}


def apply_matrix(
    classification: str,
    stage: str,
    mentoria_used: int,
    cap: int,
    confidence: str,
) -> str:
    """Decide ação ∈ {mentoria, conteudo, skip} aplicando matriz + cap + confiança.

    `stage` aqui é o `stage_reached` inferido pelo Haiku, não o `funnel_stage` de conversations.
    """
    if confidence == "low":
        return "skip"
    base = _MATRIX_FULL.get(classification, {}).get(stage, "skip")
    if base == "mentoria" and mentoria_used >= cap:
        return _DEMOTE_WHEN_CAP.get(stage, "skip")
    return base


async def count_mentoria_offers_this_month(db) -> int:
    """Conta dispatches com action=mentoria e status em (sent, approved) no mês local corrente.

    created_at é gravado em UTC (SQLite datetime('now')), então o início do mês local
    precisa ser convertido pra UTC antes da comparação. Sem isso, no dia 1 do mês BRT
    (início a -3h UTC) dispatches do fim do mês anterior ficariam incluídos.
    """
    start_local = now_local().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(timezone.utc)
    start_iso = start_utc.strftime("%Y-%m-%d %H:%M:%S")
    cursor = await db.execute(
        """SELECT COUNT(*) AS n FROM cold_dispatches
           WHERE action = 'mentoria'
             AND status IN ('sent', 'approved')
             AND created_at >= ?""",
        (start_iso,),
    )
    row = await cursor.fetchone()
    return int(row["n"]) if row else 0


# ───────────────────────── Scoring ─────────────────────────

_TIMING_KEYWORDS = (
    "mes que vem", "mês que vem", "volto", "retomo", "retorno", "depois",
    "proximo mes", "próximo mês", "semana que vem", "ano que vem", "mais pra frente",
)


def score_candidate(classification: str, stage: str, days_cold: float, quote: str) -> float:
    """Score maior = mais prioritário. `stage` aqui é o stage_reached inferido."""
    score = 0.0
    if stage == "link_sent":
        score += 50.0
    elif stage == "handbook_sent":
        score += 20.0
    elif stage == "only_qualifying":
        score += 5.0
    # nunca_qualificou: score base
    if classification == "abandono_checkout":
        score += 60.0  # prioridade máxima: verbalizou pedido do link e abandonou
                        # (acima de objecao_timing + bonus de keyword de retorno)
    elif classification == "objecao_timing":
        score += 30.0
        if any(kw in (quote or "").lower() for kw in _TIMING_KEYWORDS):
            score += 20.0
    elif classification == "objecao_preco":
        score += 20.0
    elif classification == "objecao_conteudo":
        score += 15.0
    elif classification == "perdido_no_ruido":
        score += 10.0  # subiu porque perdido_no_ruido + link_sent agora vira mentoria
    # Mais frescos primeiro dentro do mesmo estágio
    score += max(0.0, 30.0 - min(float(days_cold or 0), 120.0) / 4.0)
    return score


# ───────────────────────── Compositor ─────────────────────────

async def _load_history_for_compose(db, conversation_id: int, max_msgs: int = 12) -> str:
    cursor = await db.execute(
        """SELECT direction, content, sent_by, created_at
           FROM messages WHERE conversation_id = ?
           ORDER BY created_at DESC, id DESC LIMIT ?""",
        (conversation_id, max_msgs),
    )
    rows = list(reversed(await cursor.fetchall()))
    lines = []
    for m in rows:
        tag = "cliente" if m["direction"] == "inbound" else f"operador ({m['sent_by'] or 'equipe'})"
        lines.append(f"[{m['created_at']}] {tag}: {m['content']}")
    return "\n".join(lines) if lines else "(conversa vazia)"


def _parse_compose_response(response) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == COLD_COMPOSE_TOOL_NAME:
            inp = block.input or {}
            return _sanitize_caio_tone((inp.get("message") or "").strip())
    return ""


def _sanitize_caio_tone(msg: str) -> str:
    """Defesa em profundidade contra em-dash e travessão duplo.

    Regra Caio é 'nunca' em-dash, prompt instrui, mas Haiku pode escorregar.
    Substitui por vírgula + espaço preservando fluxo da frase.
    """
    if not msg:
        return msg
    return (
        msg.replace("—", ",")
        .replace("–", ",")
        .replace(" -- ", ", ")
        .replace("--", ",")
    )


async def compose_message(
    conversation_id: int,
    action: str,
    classification: str,
    quote_from_lead: str,
    contact_name: str,
    db=None,
) -> str:
    """Chama Haiku pra compor a mensagem no tom Caio, condicional à ação."""
    own = db is None
    if own:
        db = await get_db()
    try:
        history_text = await _load_history_for_compose(db, conversation_id)
    finally:
        if own:
            await db.close()

    lead_name = contact_name or "(sem nome)"
    action_instruction = {
        "mentoria": (
            "Ação: ofereça uma sessão privada de 1h com o Caio. Ele abriu poucas vagas esse mês. "
            "Enquadre como recuperação personalizada, não como venda. Mentoria ajuda o lead a planejar "
            "onde aplicar o curso CDO na prática."
        ),
        "conteudo": (
            "Ação: mencione que o Caio publicou uma série recente de posts sobre atribuição em marketing "
            "que pode conversar com o que o lead estava buscando. Deixe o placeholder [link] na mensagem "
            "pro operador colar. Não peça compra."
        ),
    }.get(action, "Ação indefinida.")

    user_content = (
        f"Lead: {lead_name}\n"
        f"Classificação inferida: {classification}\n"
        f"Citação do lead para referenciar: \"{quote_from_lead}\"\n\n"
        f"{action_instruction}\n\n"
        f"## Histórico recente\n{history_text}\n\n"
        "Escreva a mensagem para o Caio enviar agora. Cite literalmente o trecho da citação "
        "ao referenciar o que o lead disse antes, usando marcador temporal vago como "
        "\"lá em [mês]\" ou \"você me falou que\". Retorne via tool cold_compose_message."
    )

    try:
        client = get_anthropic_client()
        response = await client.messages.create(
            model=settings.claude_haiku_model,
            max_tokens=1024,
            system=COLD_COMPOSE_SYSTEM_PROMPT,
            tools=[COLD_COMPOSE_TOOL],
            tool_choice={"type": "tool", "name": COLD_COMPOSE_TOOL_NAME},
            messages=[{"role": "user", "content": user_content}],
        )
        return _parse_compose_response(response)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cold compose failed conv=%s: %s", conversation_id, exc)
        return ""


# ───────────────────────── Preview pipeline ─────────────────────────

async def run_preview(db=None, limit: int = PREVIEW_LIMIT) -> list[dict[str, Any]]:
    """Pipeline completo para o botão: seleciona, classifica (inclui stage_reached),
    aplica matriz sobre stage_reached (não sobre funnel_stage volátil), compõe, grava."""
    own = db is None
    if own:
        db = await get_db()

    try:
        candidates = await select_cold_candidates(db, limit=CANDIDATE_POOL)
        if not candidates:
            return []

        mentoria_used = await count_mentoria_offers_this_month(db)
        cap = settings.cold_mentoria_monthly_cap

        # Classifica em paralelo (retorna classification + stage_reached + quote + confidence)
        classify_tasks = [classify_conversation(c["id"], db=db) for c in candidates]
        classifications = await asyncio.gather(*classify_tasks, return_exceptions=False)

        enriched = []
        for cand, classif in zip(candidates, classifications):
            enriched.append({**cand, **classif})

        # Prioriza pelo stage_reached inferido + classification + frescor
        enriched.sort(
            key=lambda x: score_candidate(
                x["classification"],
                x["stage_reached"],
                x.get("days_cold") or 0.0,
                x.get("quote_from_lead", ""),
            ),
            reverse=True,
        )

        mentoria_allocated = mentoria_used
        decided: list[dict[str, Any]] = []
        for e in enriched:
            action = apply_matrix(
                e["classification"],
                e["stage_reached"],
                mentoria_allocated,
                cap,
                e["confidence"],
            )
            if action == "mentoria":
                mentoria_allocated += 1
            decided.append({**e, "action": action})

        non_skip = [d for d in decided if d["action"] != "skip"]
        skip = [d for d in decided if d["action"] == "skip"]
        visible = (non_skip + skip)[:limit]

        compose_pairs: list[tuple[int, asyncio.Task]] = []
        for idx, item in enumerate(visible):
            if item["action"] == "skip":
                continue
            compose_pairs.append(
                (idx, compose_message(
                    item["id"],
                    item["action"],
                    item["classification"],
                    item.get("quote_from_lead", ""),
                    item.get("contact_name", ""),
                    db=db,
                ))
            )

        compose_results = await asyncio.gather(*[p[1] for p in compose_pairs], return_exceptions=False)
        for (idx, _), msg in zip(compose_pairs, compose_results):
            visible[idx]["message"] = msg or ""

        results: list[dict[str, Any]] = []
        for item in visible:
            dispatch_id = await _insert_preview_row(db, item)
            results.append({
                "item_id": uuid.uuid4().hex,
                "dispatch_id": dispatch_id,
                "conversation_id": item["id"],
                "phone_number": item["phone_number"],
                "contact_name": item.get("contact_name"),
                "funnel_stage": item.get("funnel_stage"),  # estado atual, só pra referência
                "stage_reached": item["stage_reached"],     # inferido, usado na matriz
                "classification": item["classification"],
                "confidence": item["confidence"],
                "quote_from_lead": item.get("quote_from_lead", ""),
                "reasoning": item.get("reasoning", ""),
                "action": item["action"],
                "message": item.get("message", ""),
                "days_cold": float(item.get("days_cold") or 0.0),
            })

        await db.commit()
        return results
    finally:
        if own:
            await db.close()


async def _insert_preview_row(db, item: dict[str, Any]) -> int:
    cursor = await db.execute(
        """INSERT INTO cold_dispatches
           (conversation_id, classification, confidence, quote_from_lead, reasoning,
            stage_reached, action, message_draft, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'previewed')""",
        (
            item["id"],
            item["classification"],
            item["confidence"],
            item.get("quote_from_lead", ""),
            item.get("reasoning", ""),
            item.get("stage_reached", "nunca_qualificou"),
            item["action"],
            item.get("message", "") if item["action"] != "skip" else None,
        ),
    )
    return cursor.lastrowid


# ───────────────────────── Rate limit envio ─────────────────────────

def next_delay() -> float:
    """60s + uniform(-20, +40) = janela 40-100s, igual ao D-1."""
    return 60.0 + random.uniform(-20.0, 40.0)


async def execute_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Dispara mensagens aprovadas sequencialmente com jitter 40-100s.

    items: list of {dispatch_id: int, conversation_id: int, message: str}
    """
    sent = 0
    failed = 0
    for idx, item in enumerate(items):
        if idx > 0:
            await asyncio.sleep(next_delay())
        dispatch_id = item["dispatch_id"]
        conv_id = item["conversation_id"]
        message = item["message"]
        try:
            db = await get_db()
            try:
                await send_and_record(db, conv_id, message, operator="cold_rewarm")
                await db.execute(
                    """UPDATE cold_dispatches
                       SET status = 'sent',
                           message_sent = ?,
                           updated_at = datetime('now')
                       WHERE id = ?""",
                    (message, dispatch_id),
                )
                await db.commit()
                sent += 1
            finally:
                await db.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("cold execute failed dispatch=%s conv=%s: %s", dispatch_id, conv_id, exc)
            failed += 1
            try:
                db = await get_db()
                try:
                    await db.execute(
                        """UPDATE cold_dispatches
                           SET status = 'failed', updated_at = datetime('now')
                           WHERE id = ?""",
                        (dispatch_id,),
                    )
                    await db.commit()
                finally:
                    await db.close()
            except Exception:
                logger.exception("cold execute failed to mark failed dispatch=%s", dispatch_id)
    return {"sent": sent, "failed": failed}


# ───────────────────────── Reward hook (inbound) ─────────────────────────

async def mark_cold_response_received(conversation_id: int, inbound_msg_id: int) -> None:
    """Ao receber inbound, marca responded_at no cold_dispatch mais recente dessa conv (se <7d)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id FROM cold_dispatches
               WHERE conversation_id = ?
                 AND status = 'sent'
                 AND responded_at IS NULL
                 AND datetime(updated_at) >= datetime('now', '-7 days')
               ORDER BY updated_at DESC LIMIT 1""",
            (conversation_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return
        dispatch_id = row["id"]

        msg_cursor = await db.execute(
            "SELECT created_at FROM messages WHERE id = ?",
            (inbound_msg_id,),
        )
        msg_row = await msg_cursor.fetchone()
        if not msg_row:
            return
        responded_at = msg_row["created_at"]

        await db.execute(
            "UPDATE cold_dispatches SET responded_at = ?, updated_at = datetime('now') WHERE id = ?",
            (responded_at, dispatch_id),
        )
        await db.commit()
        logger.info("cold response registered dispatch=%s conv=%s", dispatch_id, conversation_id)
    finally:
        await db.close()
