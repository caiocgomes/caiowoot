# Passo 2 — Retomada de sessão

## 1. Leitura do estado

Leia `.reversa/state.json` e `.reversa/plan.md`.

## 2. Verificação de versão

Compare `.reversa/version` com o npm registry. Se houver versão mais nova, informe discretamente:
> "💡 Nova versão disponível. Execute `npx reversa update` quando quiser atualizar."

## 3. Saudação

Diga: "[Nome], bem-vindo de volta ao Reversa! 🎼"

## 4. Resumo de progresso

Mostre:
- ✅ Fases concluídas (campo `completed` do state.json)
- 🔄 Fase atual (campo `phase`) com a última tarefa registrada em `checkpoints`
- ⏳ Próximas fases (campo `pending`)

Exemplo:
> "Progresso atual:
> ✅ Reconhecimento concluído
> 🔄 Escavação em andamento — módulos `auth` e `orders` analisados, `payments` e `users` pendentes
> ⏳ Interpretação, Geração, Revisão"

## 5. Modo de resposta a lacunas

Se `answer_mode` for `"file"`:
> "Lembre-se: suas respostas às perguntas devem ser preenchidas em `_reversa_sdd/questions.md`. Me avise quando terminar."

Se `answer_mode` for `"chat"` (padrão):
> Continue normalmente — farei as perguntas aqui no chat.

## 6. Confirmação

Pergunte apenas: "Continuamos de onde paramos? (CONTINUAR para seguir)"

Após confirmação, retome a próxima tarefa pendente no plano (`.reversa/plan.md`).

**🚫 Não ofereça `/clear` + `/reversa` neste momento.** O usuário acabou de retomar a sessão; pedir para limpar e reabrir agora é redundante. O prompt de pausa entre etapas (descrito em `SKILL.md`, seção "Checkpoint preventivo entre etapas") só vale **depois** que um agente concluir trabalho dentro desta sessão, nunca na própria saudação de retomada.

Consulte `references/checkpoint-guide.md` para as regras de escrita no state.json.
