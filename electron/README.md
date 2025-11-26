# Video Downloader Pro - Electron App

Este guia explica como executar e compilar o aplicativo desktop.

## Pré-requisitos

1. **Node.js** (v18 ou superior): [Download](https://nodejs.org/)
2. **Python 3** com as dependências instaladas:
   ```bash
   pip install -r requirements.txt
   ```

## Estrutura do Projeto

```
youtube_downloader/
├── app.py                 # Backend Flask
├── templates/             # Templates HTML
├── requirements.txt       # Dependências Python
├── electron/              # Aplicativo Electron
│   ├── main.js           # Processo principal
│   ├── preload.js        # Script de preload
│   ├── package.json      # Configuração Electron
│   └── icons/            # Ícones do app
└── downloads/            # Pasta de downloads
```

## Como Executar em Desenvolvimento

### 1. Instalar dependências do Electron

```bash
cd electron
npm install
```

### 2. Executar o aplicativo

```bash
npm start
```

Isso irá:

1. Iniciar automaticamente o servidor Flask (Python)
2. Abrir a janela do aplicativo

## Como Compilar para Distribuição

### Para macOS:

```bash
cd electron
npm run build:mac
```

O instalador `.dmg` será gerado em `electron/dist/`.

### Para Windows:

```bash
cd electron
npm run build:win
```

O instalador `.exe` será gerado em `electron/dist/`.

### Para Linux:

```bash
cd electron
npm run build:linux
```

O `.AppImage` será gerado em `electron/dist/`.

## Criando Ícones

Para um app profissional, você precisa criar ícones:

- **macOS**: `icons/icon.icns` (arquivo .icns)
- **Windows**: `icons/icon.ico` (256x256)
- **Linux**: `icons/icon.png` (512x512)

Você pode usar ferramentas como [IconKitchen](https://icon.kitchen/) ou [Electron Icon Maker](https://www.npmjs.com/package/electron-icon-maker).

## Notas Importantes

1. **Python no PATH**: O usuário final precisa ter Python 3 instalado e acessível no PATH do sistema.

2. **Distribuição com Python embutido**: Para distribuir sem exigir Python instalado, você precisaria usar ferramentas como PyInstaller para empacotar o backend separadamente.

3. **Primeira execução**: Na primeira execução, pode demorar alguns segundos para o servidor Flask iniciar.

## Solução de Problemas

### "Erro ao iniciar o servidor"

- Verifique se o Python 3 está instalado: `python3 --version`
- Verifique se as dependências estão instaladas: `pip install -r requirements.txt`

### Porta já em uso

- A aplicação usa a porta 54321. Certifique-se de que não há outro processo usando essa porta.

### Tela branca

- Aguarde alguns segundos, o servidor Flask pode estar iniciando.
- Verifique o console do DevTools (View > Toggle Developer Tools) para erros.
