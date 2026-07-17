## 1. HTML: Reestruturar header e remover tabs

- [x] 1.1 Remover o `#sidebar-tabs` div com as 4 tabs do `index.html`
- [x] 1.2 Reestruturar `#sidebar-header` para: botão ☰ (id=tools-menu-btn) + título "CaioWoot" (id=sidebar-title) + notif/gear buttons
- [x] 1.3 Adicionar dropdown menu `#tools-menu` após o header com 3 items (Conhecimento, Aprendizado, Campanhas) cada um com ícone + nome + hint
- [x] 1.4 Adicionar botão "← Conversas" (id=tools-back-btn, inicialmente hidden) no header para voltar de ferramentas

## 2. CSS: Estilos do novo layout

- [x] 2.1 Remover estilos de `#sidebar-tabs` e `.sidebar-tab` do `sidebar.css`
- [x] 2.2 Adicionar estilos para `#tools-menu-btn` (botão ☰ no header)
- [x] 2.3 Adicionar estilos para `#tools-menu` (dropdown: border-bottom, bg white, hidden by default)
- [x] 2.4 Adicionar estilos para `.tools-menu-item` (padding, hover, ícone + texto + hint)
- [x] 2.5 Adicionar estilos para `#tools-back-btn` (botão ← Conversas)
- [x] 2.6 Adicionar estilos para `#sidebar-title` (texto do header que muda entre "CaioWoot" e nome da ferramenta)
- [x] 2.7 Ajustar `mobile.css` para garantir min-height 44px nos items do menu e touch targets adequados

## 3. JS: Lógica de navegação

- [x] 3.1 Criar função `toggleToolsMenu()` que abre/fecha o dropdown
- [x] 3.2 Adicionar event listener para fechar menu ao clicar fora
- [x] 3.3 Refatorar `switchTab()` para o novo modelo: quando 'conversations', mostrar lista + search + restaurar header "CaioWoot"; quando ferramenta, esconder lista, mostrar painel da ferramenta, atualizar header com "← NomeDaFerramenta"
- [x] 3.4 Criar função `backToConversations()` chamada pelo botão ← que faz switchTab('conversations')
- [x] 3.5 Expor novas funções no window (toggleToolsMenu, backToConversations)
- [x] 3.6 Garantir que o search wrapper só aparece quando em conversas

## 4. Validação

- [x] 4.1 Verificar que conversas é o estado default ao carregar
- [x] 4.2 Verificar que ☰ abre dropdown com 3 ferramentas
- [x] 4.3 Verificar que selecionar ferramenta fecha dropdown e mostra conteúdo correto
- [x] 4.4 Verificar que ← Conversas volta ao estado default
- [x] 4.5 Verificar que click outside fecha o dropdown
- [x] 4.6 Rodar `uv run pytest tests/ -x -q` para garantir que nada quebrou
