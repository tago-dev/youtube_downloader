# Video Downloader Pro - Desktop App (Electron)

Aplicativo desktop para baixar vídeos do **YouTube**, **Instagram** e **Twitter/X**.

## Pré-requisitos

1. **Node.js** (v18+): [Download](https://nodejs.org/)
2. **Python 3** com dependências instaladas:
   ```bash
   pip install -r requirements.txt
   ```

## Estrutura

```
electron/
├── main.js          # Processo principal (splash, tray, backend)
├── preload.js       # APIs seguras expostas ao frontend
├── package.json     # Configuração e build
└── icons/           # Ícones do app (icon.png, icon.ico)
```

## Funcionalidades do Desktop

- 🚀 **Splash Screen** animada enquanto o backend carrega
- 🔔 **Notificações nativas** quando o download termina
- 📂 **Abrir pasta de downloads** direto do app
- 🖥️ **System Tray** com menu de contexto
- 🔒 **Instância única** - não abre o app duplicado
- 🍎 **macOS**: Barra de título integrada, minimiza pra tray
- 📋 **Menu nativo** traduzido (Editar, Visualizar, Janela)
- ⚡ **Healthcheck** - monitora se o backend está vivo

## Desenvolvimento

```bash
# Instalar dependências
cd electron
npm install

# Executar em modo dev (com DevTools)
npm start

# Ou com variável de ambiente
npm run dev
```

## Build para Distribuição

```bash
# macOS
npm run build:mac

# Windows
npm run build:win

# Linux
npm run build:linux
```

Os binários serão gerados em `electron/dist/`.

## Ícones

Coloque seus ícones na pasta `electron/icons/`:
- `icon.png` — 512x512 (macOS, Linux)
- `icon.ico` — 256x256 (Windows)

## Troubleshooting

- **"Não foi possível iniciar o backend"**: Verifique se `python3` está no PATH
- **Tela branca**: O backend Flask pode demorar pra iniciar. Aguarde a splash sumir.
- **Porta 54321 em uso**: Encerre outros processos usando `lsof -i :54321`
