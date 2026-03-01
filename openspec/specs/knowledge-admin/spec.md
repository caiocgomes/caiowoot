## ADDED Requirements

### Requirement: Operador pode listar documentos da base de conhecimento
O sistema SHALL expor um endpoint `GET /knowledge` que retorna a lista de todos os arquivos `.md` na pasta `knowledge/`. Cada item SHALL conter o nome do arquivo (sem extensão) e a data de última modificação.

#### Scenario: Lista com documentos existentes
- **WHEN** o operador faz GET /knowledge e existem arquivos .md na pasta
- **THEN** o sistema retorna 200 com um array contendo nome e data de modificação de cada arquivo

#### Scenario: Pasta vazia
- **WHEN** o operador faz GET /knowledge e a pasta knowledge/ está vazia
- **THEN** o sistema retorna 200 com um array vazio

### Requirement: Operador pode ler o conteúdo de um documento
O sistema SHALL expor um endpoint `GET /knowledge/{name}` que retorna o conteúdo markdown do arquivo `knowledge/{name}.md`.

#### Scenario: Documento existente
- **WHEN** o operador faz GET /knowledge/curso-cdo
- **THEN** o sistema retorna 200 com o conteúdo do arquivo curso-cdo.md

#### Scenario: Documento inexistente
- **WHEN** o operador faz GET /knowledge/nao-existe
- **THEN** o sistema retorna 404

### Requirement: Operador pode criar um novo documento
O sistema SHALL expor um endpoint `POST /knowledge` que aceita um JSON com `name` (string, kebab-case) e `content` (string, texto markdown). O sistema SHALL criar o arquivo `knowledge/{name}.md` com o conteúdo fornecido.

#### Scenario: Criação com sucesso
- **WHEN** o operador envia POST /knowledge com name="faq-precos" e content="# FAQ Preços\n..."
- **THEN** o sistema cria knowledge/faq-precos.md e retorna 201

#### Scenario: Nome já existe
- **WHEN** o operador envia POST /knowledge com name="curso-cdo" e o arquivo já existe
- **THEN** o sistema retorna 409 Conflict

#### Scenario: Nome inválido
- **WHEN** o operador envia POST /knowledge com name contendo caracteres fora de [a-z0-9-]
- **THEN** o sistema retorna 422 com mensagem de erro

### Requirement: Operador pode atualizar um documento existente
O sistema SHALL expor um endpoint `PUT /knowledge/{name}` que aceita um JSON com `content` (string) e sobrescreve o conteúdo de `knowledge/{name}.md`.

#### Scenario: Atualização com sucesso
- **WHEN** o operador envia PUT /knowledge/curso-cdo com novo conteúdo
- **THEN** o sistema sobrescreve o arquivo e retorna 200

#### Scenario: Documento inexistente
- **WHEN** o operador envia PUT /knowledge/nao-existe
- **THEN** o sistema retorna 404

### Requirement: Operador pode deletar um documento
O sistema SHALL expor um endpoint `DELETE /knowledge/{name}` que remove o arquivo `knowledge/{name}.md`.

#### Scenario: Deleção com sucesso
- **WHEN** o operador envia DELETE /knowledge/faq-precos
- **THEN** o sistema remove o arquivo e retorna 200

#### Scenario: Documento inexistente
- **WHEN** o operador envia DELETE /knowledge/nao-existe
- **THEN** o sistema retorna 404

### Requirement: Endpoints validam contra path traversal
O sistema SHALL rejeitar qualquer `name` que contenha `/`, `..`, ou caracteres que permitam escapar da pasta `knowledge/`. A validação SHALL ocorrer antes de qualquer operação no filesystem.

#### Scenario: Tentativa de path traversal
- **WHEN** o operador envia GET /knowledge/../.env
- **THEN** o sistema retorna 422 sem acessar o filesystem fora de knowledge/

### Requirement: Interface web exibe aba de base de conhecimento
A interface do operador SHALL ter uma aba "Base de Conhecimento" que lista os documentos disponíveis. O operador SHALL poder selecionar um documento para visualizar e editar seu conteúdo em um editor de texto. O operador SHALL poder criar novos documentos e deletar existentes.

#### Scenario: Navegar para aba de conhecimento
- **WHEN** o operador clica na aba "Base de Conhecimento"
- **THEN** o sistema exibe a lista de documentos carregada via GET /knowledge

#### Scenario: Editar documento existente
- **WHEN** o operador seleciona um documento da lista e altera o conteúdo
- **THEN** o operador pode salvar via botão que faz PUT /knowledge/{name}

#### Scenario: Criar novo documento
- **WHEN** o operador clica em "Novo documento", preenche nome e conteúdo
- **THEN** o sistema cria o documento via POST /knowledge e atualiza a lista

#### Scenario: Deletar documento
- **WHEN** o operador clica em deletar em um documento
- **THEN** o sistema pede confirmação e, se confirmado, faz DELETE /knowledge/{name}
