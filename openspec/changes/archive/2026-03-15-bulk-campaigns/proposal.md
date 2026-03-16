## Why

O time de marketing precisa enviar mensagens em massa para potenciais compradores de workshops e cursos. Hoje não existe nenhuma ferramenta interna para isso, e disparos manuais são inviáveis acima de 20 contatos. O sistema precisa evitar detecção de spam pela Meta, que desconecta a sessão do WhatsApp por 24h quando identifica comportamento automatizado.

## What Changes

- Upload de CSV com contatos (telefone, nome) cria uma campanha
- Operador escreve mensagem base, Claude gera 8 variações genuinamente diferentes
- Operador revisa e aprova variações antes do disparo
- Disparo sequencial com intervalo aleatório configurável (min/max em segundos)
- Cada contato recebe uma variação sorteada aleatoriamente
- Imagem opcional enviada junto com o texto
- Dashboard de acompanhamento: enviados, falhos, pendentes
- Pausa/retomada manual da campanha
- Pausa automática após 5 falhas consecutivas (possível bloqueio da Meta)
- Reenvio de falhos com nova variação e novo timing
- Retomada após bloqueio da Meta (24h): continua de onde parou, mesma linha
- Respostas de destinatários caem como conversas normais no CaioWoot, tagueadas com a campanha de origem

## Capabilities

### New Capabilities
- `bulk-campaigns`: Gestão de campanhas de envio em massa (CRUD, upload CSV, configuração de intervalos, estados draft/running/paused/blocked/completed)
- `campaign-variations`: Geração de variações de mensagem via Claude e atribuição aleatória a contatos
- `campaign-executor`: Motor de execução de campanhas (poller, envio sequencial, detecção de bloqueio, retry)

### Modified Capabilities
- `webhook-receiver`: Taguear conversas originadas de campanhas com `origin_campaign_id`

## Impact

- **Database**: Novas tabelas `campaigns`, `campaign_contacts`, `campaign_variations`
- **Backend**: Novo serviço de execução (poller similar ao scheduler.py), novas rotas API, integração com Claude para geração de variações
- **Frontend**: Nova tab "Campanhas" no sidebar, telas de criação e detalhe de campanha
- **Evolution API**: Uso de `sendText` e `sendMedia` existentes, sem mudanças na integração
- **Webhook**: Modificação para detectar respostas a campanhas e taguear conversas
