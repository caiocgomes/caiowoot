## ADDED Requirements

### Requirement: Web App Manifest configurado para instalação
O app SHALL servir um `manifest.json` acessível na raiz com `name`, `short_name`, `start_url`, `display: standalone`, `background_color`, `theme_color` e referências aos ícones.

#### Scenario: Manifest acessível
- **WHEN** o browser acessa `/manifest.json`
- **THEN** o servidor SHALL retornar um JSON válido com `display: "standalone"` e `start_url: "/"`

#### Scenario: Ícones referenciados no manifest
- **WHEN** o browser lê o manifest
- **THEN** o manifest SHALL listar ícones de 192x192 e 512x512 pixels com `type: "image/png"` e `purpose: "any maskable"`

### Requirement: Service worker registrado
O app SHALL registrar um service worker no carregamento da página. O service worker SHALL interceptar requests e repassar diretamente para a rede (sem cache offline).

#### Scenario: Registro do service worker
- **WHEN** a página carrega
- **THEN** o browser SHALL registrar `/sw.js` como service worker

#### Scenario: Fetch passthrough
- **WHEN** o service worker intercepta um fetch
- **THEN** o request SHALL ser repassado diretamente para a rede sem cache

### Requirement: Meta tags para iOS
O `index.html` SHALL incluir meta tags `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `theme-color` e `apple-touch-icon` para suportar instalação no iOS.

#### Scenario: Instalação no iOS
- **WHEN** o usuário acessa o app no Safari iOS e escolhe "Add to Home Screen"
- **THEN** o app SHALL abrir em modo standalone (sem barra de endereço) com o ícone correto

### Requirement: Ícones do app
O app SHALL ter ícones PNG de 192x192 e 512x512 pixels com identidade visual do CaioWoot (iniciais "CW" em verde #25D366 sobre fundo branco).

#### Scenario: Ícones acessíveis
- **WHEN** o browser ou iOS solicita os ícones
- **THEN** `/icon-192.png` e `/icon-512.png` SHALL estar acessíveis e ser imagens PNG válidas
