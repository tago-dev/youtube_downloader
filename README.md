# 🎥 YouTube Downloader - WebApp

Um webapp moderno e elegante para baixar vídeos do YouTube com interface intuitiva e responsiva.

## ✨ Características

- 🎨 **Design Moderno**: Interface atraente com gradientes e animações suaves
- 📱 **Responsivo**: Funciona perfeitamente em desktop e mobile
- ⚡ **Rápido**: Download otimizado de vídeos
- 🎯 **Múltiplas Qualidades**: Escolha entre várias opções de qualidade (HD, SD, etc.)
- 🎵 **Apenas Áudio**: Opção para baixar apenas o áudio em formato MP3
- 📊 **Informações do Vídeo**: Visualize título, autor, duração e visualizações antes de baixar
- 🔒 **Seguro**: 100% seguro e sem anúncios

## 🚀 Como Usar

### Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

### Executar o Aplicativo

```bash
python app.py
```

O aplicativo estará disponível em: `http://localhost:5000`

## 📋 Dependências

- Flask 3.0.0
- pytube 15.0.0

## 💡 Funcionalidades

### Download de Vídeos

1. Cole a URL do vídeo do YouTube
2. Selecione a qualidade desejada
3. Clique em "Baixar Vídeo"
4. O arquivo será baixado automaticamente

### Informações do Vídeo

- Clique no botão "Informações" para ver detalhes do vídeo antes de baixar
- Visualize: título, autor, duração e número de visualizações

### Opções de Qualidade

- **Melhor Qualidade**: Melhor resolução disponível
- **720p HD**: Alta definição
- **480p SD**: Definição padrão
- **360p**: Qualidade baixa (menor tamanho)
- **Apenas Áudio**: Download do áudio em formato MP3

## 🎨 Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Design**: Font Awesome Icons, Google Fonts (Poppins)
- **Download**: PyTube

## ⚠️ Notas Importantes

- Certifique-se de ter uma conexão estável com a internet
- O download pode levar alguns minutos dependendo do tamanho do vídeo
- Respeite os direitos autorais dos criadores de conteúdo
- Use apenas para fins pessoais e educacionais

## 🐛 Solução de Problemas

Se encontrar problemas com o pytube, tente atualizar para a versão mais recente:

```bash
pip install --upgrade pytube
```

## 📝 Licença

Este projeto é livre para uso pessoal e educacional.

---

Desenvolvido com ❤️ usando Flask e PyTube
