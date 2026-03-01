## Context

O CaioWoot tem uma pasta `knowledge/` com arquivos markdown que são carregados pelo `knowledge.py` e injetados no prompt do Haiku. Hoje são 7 arquivos (~18KB). O operador precisa editar manualmente os arquivos pra atualizar preços ou adicionar informações novas.

A interface é um SPA vanilla (HTML + JS, sem framework) com sidebar de conversas e área principal. O backend é FastAPI com rotas em `app/routes/`. Os arquivos estáticos são servidos via `StaticFiles` montado na raiz.

## Goals / Non-Goals

**Goals:**
- Operador consegue criar, editar e deletar documentos da base de conhecimento pela interface web
- Zero fricção: abrir aba, editar, salvar. Sem login, sem workflow de aprovação
- As mudanças são refletidas imediatamente nas próximas gerações de draft (hot-reload já existe)

**Non-Goals:**
- Versionamento ou histórico de alterações dos documentos
- Editor rich-text ou preview de markdown. Textarea puro é suficiente
- Controle de acesso ou permissões (app é single-operator)
- Validação de conteúdo markdown

## Decisions

**1. Rota dos endpoints: `/knowledge` como prefixo**

Os endpoints ficam em `app/routes/knowledge.py` registrados com prefix no router. Segue o padrão dos outros routers (`conversations`, `messages`). Alternativa seria um sub-app separado, mas o projeto é simples demais pra justificar.

**2. Frontend: aba com toggle, não página separada**

A UI ganha duas abas no sidebar-header: "Conversas" e "Base de Conhecimento". Clicar em "Base de Conhecimento" substitui a lista de conversas pela lista de docs + editor no main. Clicar em "Conversas" volta ao estado atual. Alternativa seria uma página/rota separada, mas o app é um SPA simples e navegar entre páginas quebraria o fluxo.

**3. Editor: textarea simples com monospace**

Sem CodeMirror, sem Monaco, sem dependência externa. Um textarea com font monospace, botão de salvar, botão de deletar. O conteúdo é markdown puro, o operador já escreve markdown nos arquivos atuais. Adicionar um editor complexo não melhora o workflow pra esse volume de conteúdo.

**4. Validação de nome: regex `^[a-z0-9][a-z0-9-]*$`**

Nomes de arquivo são kebab-case. A validação acontece no backend antes de qualquer operação de filesystem. Isso garante que o nome vira um `.md` seguro e impede path traversal. O frontend também valida antes de submeter.

**5. O mount do StaticFiles precisa vir depois das rotas de API**

O `app.mount("/", StaticFiles(...))` já está no final do `main.py`, o que significa que as rotas registradas com `include_router` têm prioridade. Os novos endpoints `/knowledge` não vão conflitar com o static mount.

## Risks / Trade-offs

**Sem confirmação de save** → Operador pode sobrescrever conteúdo sem querer. Mitigação: o volume é baixo, e se necessário, git no servidor resolve. Não vale adicionar complexidade de undo agora.

**Sem lock** → Se dois operadores editam ao mesmo tempo, último salva ganha. Mitigação: app é single-operator. Se mudar, resolver depois.

**Delete sem undo** → Documento deletado some. Mitigação: confirmação via `confirm()` no frontend. Se precisar de mais, git.
