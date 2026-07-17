## Why

A sidebar tem 4 tabs horizontais ("Conversas", "Conhecimento", "Aprendizado", "Campanhas") que somam ~340px de largura mínima em 320px de espaço. Está estourando. Mais importante: as 4 tabs têm frequências de uso radicalmente diferentes. Conversas é 95% do tempo. As outras 3 são ferramentas de gestão usadas esporadicamente. Tratar as 4 como iguais visualmente é uma mentira hierárquica que desperdiça espaço.

## What Changes

- Remover a barra de 4 tabs horizontais
- Conversas passa a ser o estado DEFAULT da sidebar (sem tab, é o natural)
- Adicionar botão ☰ no header que abre dropdown com as 3 ferramentas (Conhecimento, Aprendizado, Campanhas)
- Ao selecionar uma ferramenta, a sidebar muda para mostrar essa seção com botão "← Conversas" para voltar
- No mobile, o mesmo padrão funciona naturalmente (a sidebar ocupa 100vw)
- Ajustar switchTab/router para o novo modelo de navegação

## Capabilities

### New Capabilities
- `sidebar-navigation`: Navegação da sidebar com conversas como default e menu dropdown para ferramentas

### Modified Capabilities
_(nenhuma capability existente tem seus requisitos alterados, apenas a implementação de navegação muda)_

## Impact

- `app/static/index.html` — remover sidebar-tabs, adicionar botão ☰ e dropdown menu
- `app/static/css/sidebar.css` — novos estilos para menu dropdown e estado de ferramenta
- `app/static/css/mobile.css` — ajustes mobile para o novo layout
- `app/static/js/main.js` — refatorar switchTab para o novo modelo
- `app/static/js/ui/conversations.js` — ajustar para estado default
- Nenhuma mudança no backend
