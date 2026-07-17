## Context

O bot de qualificação (`auto_qualifier.py`) usa um prompt genérico que instrui a "coletar informações". O problema é que ele tenta ser útil: responde dúvidas, dá contexto sobre cursos, opina. Isso gera informação potencialmente errada e desperdiça trocas de mensagem. O operador precisa de respostas para perguntas específicas, não de um chatbot generalista.

As perguntas são configuráveis via Settings > Qualificação (`qualifying_questions` no prompt_config). Hoje são 4 perguntas: curso de interesse, experiência na área, objetivo, dúvidas específicas.

## Goals / Non-Goals

**Goals:**
- Bot opera exclusivamente como entrevistador: faz perguntas, aprofunda respostas rasas, nunca responde dúvidas
- Bot pode agrupar perguntas (mandar várias de uma vez) e fazer subperguntas para aprofundar respostas superficiais
- Resumo de handoff mapeia cada pergunta configurada para a resposta obtida (ou "não respondida")
- Quando o lead faz uma pergunta, o bot reconhece e redireciona para o atendente sem tentar responder

**Non-Goals:**
- Mudar a UI de configuração das perguntas (já existe e funciona)
- Mudar o fluxo de handoff/assume (já funciona)
- Adicionar persistência de estado entre mensagens (o bot já recebe o histórico completo)

## Decisions

### Prompt reescrito como entrevistador

O prompt atual lista regras negativas ("NUNCA fale preço"). O novo prompt define o papel positivamente: "você é um entrevistador, seu único trabalho é obter boas respostas para estas perguntas". As perguntas configuradas são injetadas como a lista de tópicos a cobrir.

Regra central: **se o lead perguntar qualquer coisa, reconheça a pergunta e diga que o atendente vai responder. Não tente responder. Volte para as perguntas pendentes.**

O bot tem liberdade para: agrupar perguntas na primeira mensagem, fazer subperguntas quando a resposta é rasa ("trabalho com dados" → "legal, onde? há quanto tempo?"), reorganizar a ordem conforme o fluxo natural da conversa.

O bot não tem liberdade para: responder dúvidas, dar opinião, explicar conteúdo de cursos, falar sobre preços ou condições, inventar informação.

### Tool schema com respostas estruturadas

O `qualify_response` tool muda para incluir um campo `answers` que mapeia cada pergunta para sua resposta (ou null se não respondida ainda). Isso substitui o `qualification_summary` de texto livre.

```python
QUALIFY_TOOL = {
    "name": "qualify_response",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "ready_for_handoff": {"type": "boolean"},
            "answers": {
                "type": "object",
                "description": "Mapa de cada pergunta configurada para a resposta extraída da conversa. Valor null se ainda não respondida. Valor string com a resposta resumida se respondida.",
                "additionalProperties": {"type": ["string", "null"]}
            }
        },
        "required": ["message", "ready_for_handoff", "answers"]
    }
}
```

### Critério de handoff baseado nas respostas

O bot faz handoff quando: (a) todas as perguntas têm resposta não-null, OU (b) atingiu o limite de 4 trocas. O `answers` sempre é incluído no resumo de qualificação, mesmo que incompleto.

### Resumo de handoff estruturado

O `qualification_summary` que hoje é texto livre passa a ser construído a partir do `answers`: lista cada pergunta com sua resposta ou "Não respondida". Isso facilita a leitura pelo operador no context panel.

## Risks / Trade-offs

**Respostas podem não caber perfeitamente nas perguntas configuradas.** O lead pode dar informação que cruza múltiplas perguntas numa frase só. Mitigação: o prompt instrui o bot a extrair e distribuir a informação nas perguntas certas.

**O bot pode parecer robótico demais se só faz perguntas.** Mitigação: o prompt permite tom informal e subperguntas naturais. Ele pode dizer "que legal!" antes de aprofundar, só não pode tentar responder dúvidas.

**Perguntas configuradas podem mudar e o schema `answers` não tem chaves fixas.** Isso é intencional: `additionalProperties` aceita qualquer chave string. O bot recebe as perguntas no prompt e usa os textos delas como chaves no `answers`.
