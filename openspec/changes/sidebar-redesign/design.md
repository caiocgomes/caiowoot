## Context

A sidebar do CaioWoot tem 320px de largura e atualmente usa 4 tabs horizontais para navegação. As tabs estão estourando o espaço disponível. O operador passa 95% do tempo em Conversas.

## Goals / Non-Goals

**Goals:**
- Conversas como estado default sem tab, ocupando 100% do espaço
- Ferramentas (Conhecimento, Aprendizado, Campanhas) acessíveis via menu dropdown no header
- Navegação fluida: 1 clique para abrir ferramenta, 1 clique para voltar
- Funcionar em desktop (320px sidebar) e mobile (100vw)
- Escalar para novas ferramentas futuras sem redesign

**Non-Goals:**
- Mudar a funcionalidade das ferramentas (apenas a navegação)
- Mudar o layout do main area
- Adicionar animações complexas

## Decisions

### Estrutura do header

O header terá 3 elementos:
```
┌──────────────────────────────┐
│ ☰  CaioWoot           🔔  ⚙ │
└──────────────────────────────┘
```

O ☰ (menu hamburger) abre um dropdown popover com as ferramentas. O WS dot fica antes do título. O notif button e gear ficam à direita.

Quando uma ferramenta está ativa, o header muda para:
```
┌──────────────────────────────┐
│ ←  📚 Conhecimento        ⚙ │
└──────────────────────────────┘
```

O ← é um botão que volta para Conversas. O ícone + nome da ferramenta substitui "CaioWoot".

### Dropdown menu

```html
<div id="tools-menu" class="tools-menu">
  <button onclick="switchTab('knowledge')" class="tools-menu-item">
    <span class="tools-menu-icon">📚</span>
    <span>Conhecimento</span>
    <span class="tools-menu-hint">Base de conhecimento dos cursos</span>
  </button>
  <button onclick="switchTab('review')" class="tools-menu-item">
    <span class="tools-menu-icon">🧠</span>
    <span>Aprendizado</span>
    <span class="tools-menu-hint">Revisão de anotações e regras</span>
  </button>
  <button onclick="switchTab('campaigns')" class="tools-menu-item">
    <span class="tools-menu-icon">📢</span>
    <span>Campanhas</span>
    <span class="tools-menu-hint">Envio em massa</span>
  </button>
</div>
```

O dropdown aparece abaixo do header, com sombra, e fecha ao clicar fora ou ao selecionar uma opção. Estilo: fundo branco, items com ícone + título + descrição curta.

### Mudança no switchTab

O `switchTab()` atual esconde/mostra painéis de sidebar e main. A lógica base continua a mesma, mas:

1. Quando `switchTab('conversations')`: mostra conversation-list + search, esconde ferramentas, header volta a "CaioWoot"
2. Quando `switchTab('knowledge'|'review'|'campaigns')`: esconde conversation-list + search, mostra o painel da ferramenta, header muda para "← NomeDaFerramenta"

O menu dropdown fecha automaticamente ao selecionar.

### Fechamento do menu

Click outside fecha o menu (event listener no document). A mesma lógica usada no schedule-dropdown.

### Estado visual das ferramentas no menu

Quando uma ferramenta está ativa, seu item no menu pode ter um indicador (dot ou fundo destacado). Mas como o menu fecha ao selecionar, isso é menos relevante.

## Risks / Trade-offs

**Discoverability reduzida:** Novos operadores não vão descobrir as ferramentas sozinhos. Para ferramenta interna com operadores treinados, isso é aceitável.

**1 clique extra:** Ir de Conversas para uma ferramenta é 2 cliques (☰ → selecionar) em vez de 1 (tab direta). Voltar é 1 clique (← Conversas). Aceitável pela frequência de uso.

**Mobile:** O dropdown precisa ser touch-friendly (items com min-height 44px). O ← Conversas precisa ser acessível no mobile chat view.
