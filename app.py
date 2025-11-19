import os
from pytubefix import YouTube
from flask import Flask, request, send_file, render_template_string, jsonify
import re

app = Flask(__name__)

if not os.path.exists('downloads'):
    os.makedirs('downloads')

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader - Download de Vídeos</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 24px;
            padding: 50px 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            animation: fadeIn 0.5s ease-in;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header i {
            font-size: 60px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }

        h1 {
            color: #333;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 16px;
            font-weight: 400;
        }

        .form-group {
            margin-bottom: 25px;
        }

        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 10px;
            font-size: 14px;
        }

        input[type="text"] {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 15px;
            font-family: 'Poppins', sans-serif;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }

        select {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 15px;
            font-family: 'Poppins', sans-serif;
            background: #f8f9fa;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        select:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        }

        .btn-group {
            display: flex;
            gap: 15px;
            margin-top: 30px;
        }

        button {
            flex: 1;
            padding: 16px 30px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            font-family: 'Poppins', sans-serif;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: #f0f0f0;
            color: #666;
        }

        .btn-secondary:hover {
            background: #e0e0e0;
        }

        .video-info {
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }

        .video-info.show {
            display: block;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .video-info h3 {
            color: #333;
            font-size: 18px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .video-info p {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 8px;
        }

        .video-info strong {
            color: #333;
        }

        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }

        .loading.show {
            display: block;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            color: #666;
            font-size: 14px;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 12px;
            margin-top: 20px;
            display: none;
        }

        .alert.show {
            display: block;
            animation: slideIn 0.3s ease;
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }

        @media (max-width: 768px) {
            .container {
                padding: 30px 20px;
            }

            h1 {
                font-size: 24px;
            }

            .btn-group {
                flex-direction: column;
            }
        }

        .features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #e0e0e0;
        }

        .feature {
            text-align: center;
        }

        .feature i {
            font-size: 24px;
            color: #667eea;
            margin-bottom: 8px;
        }

        .feature p {
            font-size: 12px;
            color: #666;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <i class="fab fa-youtube"></i>
            <h1>YouTube Downloader</h1>
            <p class="subtitle">Baixe seus vídeos favoritos de forma rápida e fácil</p>
        </div>

        <form id="downloadForm">
            <div class="form-group">
                <label for="url">
                    <i class="fas fa-link"></i> URL do Vídeo
                </label>
                <input 
                    type="text" 
                    id="url" 
                    name="url" 
                    placeholder="Cole aqui a URL do vídeo do YouTube (ex: https://youtube.com/watch?v=...)" 
                    required
                >
            </div>

            <div class="form-group">
                <label for="quality">
                    <i class="fas fa-sliders-h"></i> Qualidade
                </label>
                <select id="quality" name="quality">
                    <option value="highest">Melhor Qualidade (Recomendado)</option>
                    <option value="720p">720p - HD</option>
                    <option value="480p">480p - SD</option>
                    <option value="360p">360p - Baixa</option>
                    <option value="audio">Apenas Áudio (MP3)</option>
                </select>
            </div>

            <div class="btn-group">
                <button type="button" onclick="getVideoInfo()" class="btn-secondary">
                    <i class="fas fa-info-circle"></i> Informações
                </button>
                <button type="submit" class="btn-primary">
                    <i class="fas fa-download"></i> Baixar Vídeo
                </button>
            </div>
        </form>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-text">Processando seu vídeo...</p>
        </div>

        <div class="video-info" id="videoInfo"></div>
        
        <div class="alert alert-success" id="successAlert"></div>
        <div class="alert alert-error" id="errorAlert"></div>

        <div class="features">
            <div class="feature">
                <i class="fas fa-bolt"></i>
                <p>Download Rápido</p>
            </div>
            <div class="feature">
                <i class="fas fa-hd-video"></i>
                <p>Alta Qualidade</p>
            </div>
            <div class="feature">
                <i class="fas fa-shield-alt"></i>
                <p>100% Seguro</p>
            </div>
        </div>
    </div>

    <script>
        const form = document.getElementById('downloadForm');
        const loading = document.getElementById('loading');
        const videoInfo = document.getElementById('videoInfo');
        const successAlert = document.getElementById('successAlert');
        const errorAlert = document.getElementById('errorAlert');

        function showLoading() {
            loading.classList.add('show');
            hideAlerts();
        }

        function hideLoading() {
            loading.classList.remove('show');
        }

        function hideAlerts() {
            successAlert.classList.remove('show');
            errorAlert.classList.remove('show');
            videoInfo.classList.remove('show');
        }

        function showSuccess(message) {
            successAlert.textContent = message;
            successAlert.classList.add('show');
        }

        function showError(message) {
            errorAlert.textContent = message;
            errorAlert.classList.add('show');
        }

        async function getVideoInfo() {
            const url = document.getElementById('url').value;
            if (!url) {
                showError('Por favor, insira uma URL válida do YouTube');
                return;
            }

            showLoading();
            hideAlerts();

            try {
                const response = await fetch('/video-info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();
                hideLoading();

                if (data.error) {
                    showError(data.error);
                } else {
                    videoInfo.innerHTML = `
                        <h3><i class="fas fa-video"></i> Informações do Vídeo</h3>
                        <p><strong>Título:</strong> ${data.title}</p>
                        <p><strong>Autor:</strong> ${data.author}</p>
                        <p><strong>Duração:</strong> ${data.length}</p>
                        <p><strong>Visualizações:</strong> ${data.views}</p>
                    `;
                    videoInfo.classList.add('show');
                }
            } catch (error) {
                hideLoading();
                showError('Erro ao obter informações do vídeo. Verifique a URL e tente novamente.');
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = document.getElementById('url').value;
            const quality = document.getElementById('quality').value;

            showLoading();
            hideAlerts();

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        url: url,
                        quality: quality
                    })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'video.mp4';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(downloadUrl);
                    document.body.removeChild(a);
                    
                    hideLoading();
                    showSuccess('✓ Download concluído com sucesso! O arquivo foi salvo em seu computador.');
                } else {
                    const error = await response.json();
                    hideLoading();
                    showError(error.error || 'Erro ao fazer download do vídeo.');
                }
            } catch (error) {
                hideLoading();
                showError('Erro ao processar o download. Verifique a URL e tente novamente.');
            }
        });
    </script>
</body>
</html>
    ''')

@app.route('/video-info', methods=['POST'])
def video_info():
    try:
        data = request.get_json()
        print(f"Dados recebidos em /video-info: {data}")
        
        if not data:
            return jsonify({'error': 'Nenhum dado recebido'}), 400
            
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
        
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return jsonify({'error': 'URL inválida. Por favor, forneça uma URL válida do YouTube'}), 400
        
        if '/live/' in url:
            return jsonify({'error': 'Lives não podem ser baixadas. Aguarde o fim da transmissão.'}), 400
        
        print(f"Obtendo informações para: {url}")
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        duration_mins = yt.length // 60
        duration_secs = yt.length % 60
        duration_str = f"{duration_mins}m {duration_secs}s"
        
        views = f"{yt.views:,}".replace(',', '.')
        
        return jsonify({
            'title': yt.title,
            'author': yt.author,
            'length': duration_str,
            'views': views,
            'thumbnail': yt.thumbnail_url
        })
    except Exception as e:
        error_msg = str(e)
        print(f"Erro ao obter informações: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Mensagens de erro mais amigáveis
        if 'HTTP Error 400' in error_msg or 'Bad Request' in error_msg:
            return jsonify({'error': 'Não foi possível acessar este vídeo. Ele pode estar privado, indisponível ou ser uma live.'}), 400
        elif 'regex' in error_msg.lower():
            return jsonify({'error': 'Erro ao processar o vídeo. O YouTube pode ter mudado sua estrutura. Tente novamente mais tarde.'}), 400
        else:
            return jsonify({'error': f'Erro ao obter informações: {error_msg}'}), 400

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        print(f"Dados recebidos: {data}")
        
        if not data:
            return jsonify({'error': 'Nenhum dado recebido'}), 400
            
        url = data.get('url')
        quality = data.get('quality', 'highest')
        
        print(f"URL: {url}, Qualidade: {quality}")
        
        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
        
        # Validar URL do YouTube
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return jsonify({'error': 'URL inválida. Por favor, forneça uma URL válida do YouTube'}), 400
        
        # Verificar se é uma live stream
        if '/live/' in url:
            return jsonify({'error': 'Lives não podem ser baixadas. Aguarde o fim da transmissão.'}), 400
        
        print(f"Iniciando download para: {url}")
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        if quality == 'audio':
            stream = yt.streams.filter(only_audio=True).first()
            if not stream:
                return jsonify({'error': 'Não foi possível encontrar stream de áudio'}), 400
        elif quality == 'highest':
            stream = yt.streams.get_highest_resolution()
        else:
            # Tentar obter a resolução específica
            stream = yt.streams.filter(res=quality, progressive=True).first()
            if not stream:
                stream = yt.streams.get_highest_resolution()
        
        if not stream:
            return jsonify({'error': 'Nenhum stream disponível para download'}), 400
        
        print(f"Stream selecionado: {stream}")
        
        # Download do vídeo
        output_path = 'downloads'
        print(f"Baixando para: {output_path}")
        downloaded_file = stream.download(output_path=output_path)
        
        print(f"Arquivo baixado: {downloaded_file}")
        
        filename = os.path.basename(downloaded_file)
        
        return send_file(
            downloaded_file,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4' if quality != 'audio' else 'audio/mpeg'
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"Erro no download: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Mensagens de erro mais amigáveis
        if 'HTTP Error 400' in error_msg or 'Bad Request' in error_msg:
            return jsonify({'error': 'Não foi possível baixar este vídeo. Ele pode estar privado, indisponível ou ser uma live. Tente com outro vídeo.'}), 400
        elif 'regex' in error_msg.lower():
            return jsonify({'error': 'Erro ao processar o vídeo. O YouTube pode ter mudado sua estrutura. Tente atualizar a biblioteca ou usar outro vídeo.'}), 400
        else:
            return jsonify({'error': f'Erro ao fazer download: {error_msg}'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)