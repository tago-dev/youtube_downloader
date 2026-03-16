# Playdown

Aplicativo desktop nativo em Python para baixar mídia do YouTube, Instagram e Twitter/X, com interface em `customtkinter` e fila persistente.

## O que mudou

- Não depende mais de Flask, navegador, `pywebview` ou Electron para a interface principal.
- A lógica de download foi separada da interface.
- A fila de downloads continua persistida em disco e agora alimenta a UI diretamente.
- O executável passa a empacotar a GUI nativa com PyInstaller.

## Recursos

- Preview de título, autor, duração, views e thumbnail
- Seleção de formato `video` ou `audio`
- Fila de downloads com progresso em tempo real
- Cancelamento e nova tentativa de jobs com falha
- Abertura rápida da pasta de downloads
- Persistência automática da fila entre reinicializações

## Estrutura principal

- `app.py`: entrada principal do app
- `native_app.py`: entrada alternativa para a GUI nativa
- `playdown/core.py`: extração de metadados e resolução/download dos arquivos
- `playdown/queue_manager.py`: fila persistente e worker em background
- `playdown/gui.py`: interface desktop em `customtkinter`
- `playdown/paths.py`: diretórios de dados e downloads do aplicativo

## Instalação

### Com `uv` (recomendado)

```bash
uv sync
uv run python app.py
```

### Com `pip`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Gerando o executável

```bash
uv run pyinstaller YouTubeDownloader.spec
```

No macOS, o app será gerado em `dist/YouTubeDownloader.app`.

## Observações

- Os downloads são salvos em uma subpasta `Playdown` dentro da pasta padrão de downloads do sistema.
- O estado da fila é salvo no diretório de dados do usuário usando `platformdirs`.
- O modo `audio` baixa o melhor stream de áudio disponível. O arquivo final pode ser `mp3`, `m4a` ou `webm`, dependendo da origem.

## Desenvolvimento

Para validar rapidamente a sintaxe dos arquivos Python:

```bash
python3 -m compileall app.py native_app.py desktop_app.py playdown
```
