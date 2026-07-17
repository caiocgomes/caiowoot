## ADDED Requirements

### Requirement: Qualificação automática de novas conversas
Quando um lead manda a primeira mensagem, um robô responde automaticamente para coletar informações de qualificação. O robô é transparente sobre ser assistente virtual.

#### Scenario: Primeira mensagem de um lead novo
- **WHEN** uma mensagem inbound chega de um número novo (cria conversa)
- **THEN** a conversa é criada com `is_qualified = False` e o robô responde automaticamente com apresentação + primeira pergunta de qualificação

#### Scenario: Mensagem de lead em qualifying (is_qualified = False)
- **WHEN** uma mensagem inbound chega numa conversa com `is_qualified = False`
- **THEN** o robô gera e envia resposta automaticamente via Evolution API, sem gerar drafts para o operador

#### Scenario: Robô coleta informação suficiente
- **WHEN** o robô determina que tem informação suficiente (2-3 respostas úteis) ou atingiu 4 trocas
- **THEN** o robô envia mensagem de handoff, seta `is_qualified = True`, gera situation summary, e notifica via WebSocket

#### Scenario: Lead pergunta sobre preço ou condições
- **WHEN** o lead faz uma pergunta que o robô não deve responder (preço, desconto, pagamento)
- **THEN** o robô faz handoff imediato dizendo que o operador vai explicar isso

#### Scenario: Lead rejeita o robô
- **WHEN** o lead diz que quer falar com humano ou ignora as perguntas do robô
- **THEN** o robô faz handoff imediato

#### Scenario: Conversa já qualificada
- **WHEN** uma mensagem inbound chega numa conversa com `is_qualified = True`
- **THEN** o fluxo normal acontece (gerar drafts para operador)

#### Scenario: Mensagens do robô são identificáveis
- **WHEN** o robô envia uma mensagem
- **THEN** a mensagem é salva com `sent_by = "bot"` e aparece com estilo visual diferente (azul claro em vez de verde)

### Requirement: Estado visual de qualifying no frontend
Conversas em qualifying têm aparência distinta para o operador.

#### Scenario: Sidebar mostra conversas em qualifying
- **WHEN** uma conversa tem `is_qualified = False`
- **THEN** ela aparece com indicador visual amarelo/laranja na sidebar e ícone de robô

#### Scenario: Conversa qualificada muda de cor
- **WHEN** `is_qualified` muda de False para True (via handoff automático ou manual)
- **THEN** a sidebar atualiza a cor para verde/normal via WebSocket

#### Scenario: Operador abre conversa em qualifying
- **WHEN** o operador abre uma conversa com `is_qualified = False`
- **THEN** a área de composição é substituída por um banner "Robô qualificando esta conversa" com botão "Assumir conversa"

#### Scenario: Operador vê mensagens do robô em tempo real
- **WHEN** o robô envia mensagem numa conversa em qualifying
- **THEN** a mensagem aparece no chat do operador via WebSocket (o operador acompanha a conversa)
