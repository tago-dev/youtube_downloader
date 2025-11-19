# 🎥 YouTube Downloader Pro

Um webapp moderno e elegante para baixar vídeos e áudios do YouTube, construído com **Flask** e **StreamSnapper**.

## ✨ Características

- 🎨 **Design Glassmorphism**: Interface moderna com efeitos de vidro, gradientes e animações suaves (Tailwind CSS).
- 🚀 **Alta Performance**: Utiliza a biblioteca `streamsnapper` para extração rápida e confiável.
- 📊 **Progresso em Tempo Real**: Barra de progresso e logs detalhados via Server-Sent Events (SSE).
- 📱 **Responsivo**: Funciona perfeitamente em desktop e mobile.
- 🎯 **Formatos**: Suporte para Vídeo (MP4) e Áudio (MP3/M4A/WebM).
- 🖼️ **Preview**: Visualização automática da thumbnail e metadados do vídeo.
- 📝 **Histórico**: Salva seus downloads recentes localmente.

## 🛠️ Tecnologias

- **Backend**: Python 3.10+, Flask 3.0.0
- **Core**: [StreamSnapper](https://github.com/henrique-coder/streamsnapper) (Extração de mídia)
- **Frontend**: HTML5, Tailwind CSS, JavaScript (Vanilla + Axios)
- **Gerenciador de Pacotes**: uv (recomendado) ou pip

## 🚀 Como Usar

### Instalação

Recomendamos o uso do **uv** para gerenciamento de dependências.

1. Clone o repositório:

```bash
git clone https://github.com/tago-dev/youtube_downloader.git
cd youtube_downloader
```

2. Instale as dependências e rode o projeto:

```bash
# Usando uv (Recomendado)
uv sync
.venv/bin/python -m flask run --debug

# OU usando pip tradicional
pip install flask requests git+https://github.com/henrique-coder/streamsnapper.git@main
python -m flask run
```

3. Acesse no navegador:
   `http://127.0.0.1:5000`

## 🏆 Menção Honrosa

Um agradecimento especial ao meu grande amigo **Henrique "FHDP" Morreira**, criador da biblioteca `streamsnapper` e lenda viva do desenvolvimento, que tornou este projeto possível com sua ferramenta incrível e suporte técnico de elite! 🔥

---

Desenvolvido com ❤️ por Tiago
