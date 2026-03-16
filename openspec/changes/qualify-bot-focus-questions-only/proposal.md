## Why

O bot de qualificação hoje tem uma instrução genérica de "coletar informações". Na prática, quando o lead faz uma pergunta ("quanto custa?", "o curso tem certificado?"), o bot tenta ajudar, dar contexto, ou responder parcialmente. Isso é ruim por dois motivos: primeiro, o bot pode dar informação errada ou desalinhada do que o operador diria; segundo, desperdiça trocas de mensagem com respostas que não coletam nada útil. O papel do bot é estritamente perguntar, não responder.

## What Changes

- **Reformular o prompt do bot** para operar como entrevistador inteligente: ele tem uma lista de perguntas-chave e o objetivo é obter boas respostas para cada uma. Ele não precisa ir uma a uma. Pode mandar várias perguntas de uma vez na primeira mensagem, e na segunda rodada reforçar as que ficaram vagas ou foram puladas. Se a resposta for superficial ("sim, trabalho com dados"), ele pode aprofundar com subperguntas ("onde? há quanto tempo? que tipo de trabalho?"). O que importa é a qualidade das respostas, não seguir um roteiro rígido.
- **Manter a regra de nunca responder dúvidas**: se o lead perguntar algo, o bot reconhece ("boa pergunta"), diz que o atendente vai responder, e volta para as perguntas pendentes.
- **Estruturar o output do bot** para rastrear quais perguntas já têm boas respostas e quais ainda precisam de mais informação. O handoff acontece quando as perguntas foram bem respondidas (ou o limite de trocas foi atingido).
- **Entregar um resumo estruturado no handoff** com as respostas coletadas mapeadas para cada pergunta, para que o operador saiba exatamente o que foi respondido e o que ficou pendente.

## Capabilities

### New Capabilities

_Nenhuma. A mudança é comportamental dentro da capability existente._

### Modified Capabilities

- `auto-qualifying`: O comportamento do bot muda de "coletar informações de forma livre" para "fazer perguntas configuradas, aprofundar quando necessário, e nunca responder dúvidas". O bot ganha liberdade para agrupar perguntas e fazer subperguntas, mas perde a liberdade de tentar ajudar o lead. O formato do resumo de qualificação muda de texto livre para respostas estruturadas por pergunta.

## Impact

- `app/services/auto_qualifier.py` — prompt system reescrito, tool schema atualizado para incluir respostas estruturadas por pergunta e tracking de perguntas com respostas suficientes
- `app/services/prompt_config.py` — defaults das perguntas de qualificação podem precisar de ajuste
- Frontend: sem impacto visual, a mudança é no conteúdo do resumo exibido no context panel
