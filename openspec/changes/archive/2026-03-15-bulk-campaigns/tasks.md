## 1. Database

- [x] 1.1 Criar tabela `campaigns` (id, name, status, base_message, image_path, min_interval, max_interval, next_send_at, consecutive_failures, created_at)
- [x] 1.2 Criar tabela `campaign_contacts` (id, campaign_id, phone_number, name, status, variation_id, error_message, sent_at, created_at)
- [x] 1.3 Criar tabela `campaign_variations` (id, campaign_id, variation_index, variation_text, usage_count)
- [x] 1.4 Adicionar campo `origin_campaign_id` na tabela `conversations`
- [x] 1.5 Criar migrations para as novas tabelas e campo

## 2. API de Campanhas (CRUD)

- [x] 2.1 Rota POST `/campaigns` — criar campanha com upload de CSV e mensagem base
- [x] 2.2 Rota GET `/campaigns` — listar todas as campanhas com contagens de status
- [x] 2.3 Rota GET `/campaigns/{id}` — detalhe da campanha com contatos e variações
- [x] 2.4 Rota POST `/campaigns/{id}/start` — iniciar campanha (draft → running)
- [x] 2.5 Rota POST `/campaigns/{id}/pause` — pausar campanha (running → paused)
- [x] 2.6 Rota POST `/campaigns/{id}/resume` — retomar campanha (paused/blocked → running)
- [x] 2.7 Rota POST `/campaigns/{id}/retry` — reenviar contatos falhos (reset failed → pending, nova variação)

## 3. Geração de Variações

- [x] 3.1 Criar serviço `campaign_variations.py` com função `generate_variations(base_message, count=8)`
- [x] 3.2 Prompt Claude Haiku que instrui diversificação genuína (estrutura, tom, abertura, comprimento, emojis)
- [x] 3.3 Rota POST `/campaigns/{id}/generate-variations` — gerar e salvar variações
- [x] 3.4 Rota PUT `/campaigns/{id}/variations/{idx}` — editar variação individual
- [x] 3.5 Rota POST `/campaigns/{id}/regenerate-variations` — regenerar todas as variações

## 4. Executor de Campanhas

- [x] 4.1 Criar serviço `campaign_executor.py` com poller de 10s
- [x] 4.2 Lógica de pick: próximo contato pending, sortear variação (preferir menos usadas), resolver placeholders
- [x] 4.3 Envio texto-only via `sendText` da Evolution API
- [x] 4.4 Envio com imagem via `sendMedia` com recompressão JPEG aleatória (85-95%)
- [x] 4.5 Atualização de status do contato (sent/failed) e cálculo de next_send_at
- [x] 4.6 Contador de falhas consecutivas e auto-pause ao atingir 5
- [x] 4.7 Detecção de completion (sem pendentes → status completed)
- [x] 4.8 Broadcast de eventos WebSocket (campaign_progress, campaign_status)
- [x] 4.9 Iniciar poller no startup da aplicação (similar ao scheduler)

## 5. Webhook — Tagueamento de Campanhas

- [x] 5.1 No webhook de mensagem inbound, checar se phone_number existe em campaign_contacts com status sent
- [x] 5.2 Se sim, setar origin_campaign_id na conversa

## 6. Frontend — Tab Campanhas e Lista

- [x] 6.1 Adicionar tab "Campanhas" no sidebar (ao lado de Conversas, Conhecimento, Aprendizado)
- [x] 6.2 Listar campanhas no sidebar com nome, status e contagem sent/total
- [x] 6.3 Tela de criação de campanha: nome, upload CSV, mensagem base, imagem opcional, configuração de intervalos
- [x] 6.4 Botão de gerar variações e exibição das 8 variações para revisão/edição

## 7. Frontend — Detalhe e Controles

- [x] 7.1 Tela de detalhe: barra de progresso, contagens (sent/failed/pending), lista de contatos com status
- [x] 7.2 Botões de ação: Iniciar, Pausar, Retomar, Reenviar falhos
- [x] 7.3 Exibição e edição de variações no detalhe da campanha
- [x] 7.4 Atualização real-time via WebSocket (campaign_progress, campaign_status)
- [x] 7.5 Bump do cache version do app.js no index.html

## 8. Testes

- [x] 8.1 Testes do parsing de CSV e criação de campanha
- [x] 8.2 Testes do executor: envio, falha, auto-pause, completion
- [x] 8.3 Testes do retry com nova variação
- [x] 8.4 Testes do webhook tagueamento de campaign origin
- [x] 8.5 Testes da geração de variações (mock Claude)
