from app.database import get_db

PROMPT_DEFAULTS = {
    "postura": """- Você é um vendedor consultivo: entende o problema da pessoa e direciona pro curso certo
- Se o curso não for pra ela, diga isso. Não force venda
- Seja direto, sem enrolação, mas humano e acessível
- Nunca minta sobre o que o curso oferece
- Não ofereça descontos. Quando a pessoa mostrar objeção de preço, mostre valor relativo (custo por dia, ROI, comparação com MBA/bootcamp)
- Quando a pessoa estiver vaga, qualifique antes de recomendar: pergunte o que ela faz, qual o objetivo, qual a experiência com dados/IA""",
    "tom": """- Direto, informal brasileiro (sem ser coloquial demais)
- Primeira pessoa, como se fosse o Caio digitando
- Frases curtas, sem firulas
- Pode usar "vc", "pra", "tá" naturalmente
- Sem emojis excessivos (no máximo 1-2 por mensagem quando natural)""",
    "regras": """- Sempre responda em português brasileiro
- Se o cliente perguntar algo que você não sabe, diga que vai verificar
- Nunca invente informações sobre os cursos que não estejam na base de conhecimento
- Se for a primeira mensagem, foque em entender o que a pessoa precisa antes de vender
- Se souber o nome do cliente, use-o ocasionalmente de forma natural. Não repita o nome em toda mensagem""",
    "approach_direta": "Responda de forma direta e objetiva, indo direto ao ponto.",
    "approach_consultiva": "Responda de forma consultiva, fazendo perguntas de qualificação antes de recomendar.",
    "approach_casual": "Responda de forma mais casual e acolhedora, priorizando conexão humana.",
    "summary_prompt": """Analise a conversa abaixo e gere um resumo da situação estratégica em 2-3 frases.

O resumo deve descrever:
- Estágio da conversa (primeiro contato, qualificação, recomendação, objeção, fechamento)
- Perfil aparente do cliente (técnico, leigo, indeciso, objetivo claro, etc.)
- O que já foi discutido ou qualificado
- Qual o movimento estratégico esperado agora

Responda APENAS com o texto do resumo, sem formatação extra.""",
    "annotation_prompt": """Analise a interação abaixo entre a IA e o operador humano.

Seu objetivo é entender a DECISÃO ESTRATÉGICA por trás da edição (ou aceitação) do operador.
Foque no raciocínio de vendas (quando qualificar, quando recomendar, quando recuar, como lidar com objeção), NÃO em diferenças de estilo textual (tom, comprimento, escolha de palavras).

Se o operador editou:
- Descreva o que a IA propôs vs. o que o operador fez
- Explique a correção estratégica (ex: "IA recomendou curso direto, operador voltou para qualificação")
- Identifique a situação que motivou a correção

Se o operador aceitou sem editar:
- Descreva a abordagem que funcionou
- Note que foi validada por aceitação

Responda em 2-3 frases, direto ao ponto. Apenas o texto da anotação, sem formatação.""",
}


async def get_all_prompts(db=None) -> dict[str, str]:
    close_db = db is None
    if db is None:
        db = await get_db()
    try:
        rows = await db.execute("SELECT key, value FROM prompt_config")
        stored = {row["key"]: row["value"] for row in await rows.fetchall()}
        result = {}
        for key, default in PROMPT_DEFAULTS.items():
            result[key] = stored.get(key, default)
        return result
    finally:
        if close_db:
            await db.close()


async def update_prompts(updates: dict[str, str], db=None) -> None:
    close_db = db is None
    if db is None:
        db = await get_db()
    try:
        for key, value in updates.items():
            if key not in PROMPT_DEFAULTS:
                continue
            await db.execute(
                "INSERT INTO prompt_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
                (key, value),
            )
        await db.commit()
    finally:
        if close_db:
            await db.close()


async def reset_prompt(key: str, db=None) -> None:
    close_db = db is None
    if db is None:
        db = await get_db()
    try:
        await db.execute("DELETE FROM prompt_config WHERE key = ?", (key,))
        await db.commit()
    finally:
        if close_db:
            await db.close()
