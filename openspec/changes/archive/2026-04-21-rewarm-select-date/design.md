## Context

Fix pequeno e cirúrgico. Objetivo é remover o acoplamento de "ontem fixo" no filtro de candidatos do rewarm e dar ao operador controle sobre qual dia considerar. Sem adicionar complexidade de calendário ou feriados.

## Decisões-chave

### D1. Parametrizar por data, não por delta

`reference_date` é string ISO `YYYY-MM-DD`, não `days_ago=N`. Razão: data explícita é menos ambígua quando ele quer "sexta passada" (pode ser 2 ou 3 dias atrás dependendo do dia atual). Também facilita o datepicker no front.

### D2. Default inteligente só nos dias em que dói

Segunda-feira default vira "sexta passada" (3 dias atrás). Demais dias, default vira ontem. Não trato feriado na v1; se o operador clicar terça pós-feriado, default é segunda (ontem) e ele ajusta no modal se quiser. Decisão consciente de não complicar.

### D3. Sem limite de data

Operador pode escolher qualquer dia, incluindo data distante ou hoje. Bloqueio artificial não tem custo real e adiciona fricção. Se escolher hoje, o filtro mostra leads ativos de hoje, o que geralmente vira lista vazia ou irrelevante; aprendizado natural.

### D4. Modal intermediário, não inline no modal de revisão

Fluxo: botão → modal-data → preview → modal-revisão. Separar a escolha de data da revisão de sugestões mantém cada modal com uma responsabilidade. Se errou a data, fecha o modal de revisão, abre de novo, troca. Custo de 1 clique é aceitável pelo ganho de clareza.

### D5. Nome do botão

"Reesquentar D-1" sugere acoplamento a "um dia atrás". Como a funcionalidade agora é "escolha o dia", **"Reesquentar leads"** é mais honesto.

## Arquitetura

```
UI
   ├─ clique "Reesquentar leads"
   ├─ GET /rewarm/suggested-date → {date, label}
   ├─ abre rewarm-date-modal com radio [ontem | sugerido se ≠ ontem | data custom]
   ├─ operador confirma
   └─ POST /rewarm/preview {reference_date} → abre modal de revisão existente

Backend
   ├─ GET /rewarm/suggested-date
   │     retorna ontem se hoje não é segunda
   │     retorna sexta se hoje é segunda
   │
   └─ POST /rewarm/preview
         body opcional {reference_date: "YYYY-MM-DD"}
         se ausente, reference_date = (now_local - 1 day).date().isoformat()
         passa pro select_rewarm_candidates como parâmetro
```

## O que NÃO está no escopo

- Feriados brasileiros.
- Datepicker gráfico elaborado (input `type="date"` do HTML resolve).
- Limitação de range.
- Aplicar a mesma lógica no cold rewarm.
- Persistência da última data usada pra preencher default.
