## Context

O operador compõe mensagens no textarea do compose area. Hoje pode selecionar um draft gerado pela IA ou escrever do zero. Quando escreve do zero (ou edita pesadamente um draft), o texto frequentemente tem erros de digitação e frases mal construídas. Não existe um caminho para polir o texto sem regerar os drafts (que partem do contexto da conversa, não do texto do operador).

## Goals / Non-Goals

**Goals:**
- Permitir que o operador transforme um rascunho rápido em texto limpo com um clique
- Manter a semântica exata do texto original (sem adicionar ideias)
- Tom adequado para WhatsApp: português correto mas natural, não corporativo

**Non-Goals:**
- Reescrita context-aware (não precisa do histórico da conversa)
- Múltiplas variações de reescrita (é 1:1, texto entra, texto sai)
- Tracking de reescritas no learning loop (não gera edit_pair)

## Decisions

**1. Endpoint síncrono (não background task)**

O rewrite é rápido (texto curto, prompt simples, Haiku) e o operador precisa do resultado imediatamente para continuar editando ou enviar. Diferente do `generate_drafts` que roda em background e notifica via WebSocket, o rewrite retorna o texto na response HTTP.

Alternativa descartada: WebSocket como os drafts. Overhead desnecessário para uma operação que leva <2s.

**2. Serviço isolado (`app/services/text_rewrite.py`)**

Prompt e lógica separados do `draft_engine.py`. O draft engine monta contexto complexo (knowledge, few-shot, rules, situation summary). O rewrite é uma chamada Haiku com prompt fixo. Misturar os dois polui a responsabilidade do draft engine.

**3. Prompt fixo com tool_use**

Seguindo o padrão do projeto, o resultado vem via `tool_use` (como o draft_engine já faz). Prompt fixo sem variáveis de contexto. O texto do operador vai no `user` message, o system prompt define o comportamento.

**4. Botão no btn-group entre Enviar e 📎**

Posição visual: Enviar (verde, topo) > Reescrever (meio) > 📎 (baixo). O reescrever é uma ação intermediária: não envia, não anexa, transforma o texto. Fica entre os dois. No mobile, segue o layout horizontal existente.

**5. Replace direto na textarea**

O texto reescrito substitui o conteúdo do textarea. Sem preview, sem diff, sem confirmação. Ctrl+Z do browser não funciona para programmatic changes no textarea, mas o operador pode clicar reescrever de novo ou simplesmente reescrever manualmente. Dado que o texto original era um rascunho ruim, perder ele não é problema.

## Risks / Trade-offs

- **Latência perceptível**: Haiku é rápido mas não instantâneo. O botão precisa de feedback visual (loading state, disabled) para o operador saber que algo está acontecendo. → Mitigação: spinner/text "Reescrevendo..." no botão durante a chamada.
- **Texto muito curto**: Se o operador digitar "ok" e clicar reescrever, o resultado pode ser estranho. → Mitigação: validação client-side, mínimo ~10 caracteres para habilitar o botão. Ou simplesmente confiar que o operador não vai fazer isso (KISS).
- **Custo**: Cada reescrita é uma chamada Haiku. Volume baixo (operadores manuais, não automatizado), custo negligível.
