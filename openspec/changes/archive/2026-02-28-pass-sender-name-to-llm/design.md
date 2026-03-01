## Context

O `draft_engine.py` monta o prompt para o Claude Haiku com: system prompt (persona do Caio), base de conhecimento, few-shot examples (edit pairs), instrução do operador e histórico da conversa. Em nenhum momento o nome do cliente é incluído. O `contact_name` já existe em `conversations` (vindo do `pushName` do WhatsApp) e já é exibido na UI.

Separadamente, o textarea de edição de mensagens (`#draft-input`) tem `min-height: 120px` e `max-height: 300px`, o que mostra poucas linhas e dificulta a leitura de mensagens mais longas.

## Goals / Non-Goals

**Goals:**
- Passar o primeiro nome do cliente como contexto no prompt para que os drafts possam usar o nome naturalmente
- Aumentar a área visível do campo de edição para melhorar a experiência do operador

**Non-Goals:**
- Não alterar a persona ou o tom do system prompt além da orientação sobre uso do nome
- Não criar lógica sofisticada de parsing de nomes (split simples no primeiro espaço é suficiente)
- Não alterar schema do banco de dados

## Decisions

### 1. Extração do primeiro nome: split simples

O `contact_name` pode vir como "Maria Silva", "João", ou vazio. Basta `contact_name.split()[0]` para pegar o primeiro nome. Se vazio, não inclui nada no prompt.

**Alternativa descartada**: NLP para identificar primeiro nome vs sobrenome. Desnecessário para WhatsApp onde `pushName` já é o nome que a pessoa escolheu mostrar.

### 2. Onde incluir o nome no prompt

Incluir como uma linha no `user_content` dentro de `_build_prompt_parts`, logo antes da conversa atual:

```
## Cliente
Nome: {primeiro_nome}

## Conversa atual
...
```

**Alternativa descartada**: Colocar no system prompt. O nome muda por conversa, então pertence ao user content, não ao system (que é fixo).

### 3. Orientação de uso no system prompt

Adicionar ao system prompt uma regra simples: "Se souber o nome do cliente, use-o ocasionalmente de forma natural. Não repita o nome em toda mensagem."

### 4. Campo de edição: aumentar min-height e max-height

Mudar `min-height` de `120px` para `200px` e `max-height` de `300px` para `500px`, tanto no CSS quanto na função `autoResize` do JS. Isso mostra ~8-10 linhas iniciais em vez de ~4-5.

**Alternativa descartada**: Textarea expansível sem limite. Pode empurrar o resto da interface para baixo e prejudicar a usabilidade.

## Risks / Trade-offs

- **Nome estranho no pushName** (ex: "Amor", "Mãe"): baixo risco, o operador revisa e edita antes de enviar. Não vale criar lógica de filtragem.
- **pushName vazio**: tratado com fallback (não inclui seção de nome no prompt). Sem impacto.
- **Campo maior em telas pequenas**: `max-height: 500px` pode ser muito em mobile. Mitigação: `resize: vertical` já permite ajuste manual. Se necessário, media query futura.
