## MODIFIED Requirements

### Requirement: Qualificação automática de novas conversas
Quando um lead manda a primeira mensagem, um robô responde automaticamente para coletar informações de qualificação. O robô é transparente sobre ser assistente virtual. O robô opera exclusivamente como entrevistador: faz as perguntas configuradas, aprofunda respostas rasas, e NUNCA tenta responder dúvidas do lead.

#### Scenario: Primeira mensagem de um lead novo
- **WHEN** uma mensagem inbound chega de um número novo (cria conversa)
- **THEN** a conversa é criada com `is_qualified = False` e o robô responde com apresentação + as perguntas de qualificação (pode agrupar várias perguntas na mesma mensagem)

#### Scenario: Mensagem de lead em qualifying (is_qualified = False)
- **WHEN** uma mensagem inbound chega numa conversa com `is_qualified = False`
- **THEN** o robô analisa quais perguntas já foram respondidas, aprofunda respostas rasas com subperguntas, e reforça perguntas que foram puladas

#### Scenario: Lead dá resposta superficial
- **WHEN** o lead responde uma pergunta de forma vaga (ex: "sim, trabalho com dados")
- **THEN** o robô faz subperguntas para aprofundar (ex: "onde? há quanto tempo? que tipo de trabalho?") sem sair do papel de entrevistador

#### Scenario: Lead faz uma pergunta ao bot
- **WHEN** o lead faz qualquer pergunta (preço, conteúdo, certificado, duração, qualquer coisa)
- **THEN** o robô reconhece a pergunta ("boa pergunta!"), diz que o atendente vai responder sobre isso, e volta para as perguntas de qualificação pendentes. O robô NUNCA tenta responder a pergunta do lead.

#### Scenario: Todas as perguntas respondidas
- **WHEN** o robô determina que todas as perguntas configuradas têm respostas suficientes
- **THEN** o robô faz handoff com resumo estruturado mapeando cada pergunta para sua resposta

#### Scenario: Limite de trocas atingido
- **WHEN** o robô atingiu 4 trocas de mensagem
- **THEN** o robô faz handoff mesmo com perguntas pendentes, incluindo no resumo quais perguntas ficaram sem resposta

#### Scenario: Conversa já qualificada
- **WHEN** uma mensagem inbound chega numa conversa com `is_qualified = True`
- **THEN** o fluxo normal acontece (gerar drafts para operador)

#### Scenario: Mensagens do robô são identificáveis
- **WHEN** o robô envia uma mensagem
- **THEN** a mensagem é salva com `sent_by = "bot"` e aparece com estilo visual diferente (azul claro em vez de verde)

#### Scenario: Resumo de handoff é estruturado por pergunta
- **WHEN** o robô faz handoff (automático ou por limite de trocas)
- **THEN** o resumo de qualificação lista cada pergunta configurada com a resposta obtida ou "Não respondida", em vez de texto livre

#### Scenario: Tool response inclui respostas estruturadas
- **WHEN** o robô gera uma resposta via Claude
- **THEN** o tool `qualify_response` retorna um campo `answers` com mapa de pergunta → resposta (string ou null), além de `message` e `ready_for_handoff`
