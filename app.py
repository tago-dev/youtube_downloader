import os
from streamsnapper import YouTube, SupportedCookieBrowser
import requests
from flask import Flask, request, send_file, render_template, jsonify, Response
import re
import json
import time
import yt_dlp

app = Flask(__name__)

# Configuração do diretório de downloads
DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

download_progress = {}

def download_file_from_url(url, filepath, download_id=None):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if download_id:
                        percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                        download_progress[download_id] = {
                            'status': 'downloading',
                            'percent': percent,
                            'message': f'Baixando do YouTube: {percent:.1f}%'
                        }
        
        if download_id:
            download_progress[download_id] = {
                'status': 'processing',
                'percent': 100,
                'message': 'Processando arquivo...'
            }
            
    except Exception as e:
        if download_id:
            download_progress[download_id] = {
                'status': 'error',
                'percent': 0,
                'message': f'Erro: {str(e)}'
            }
        raise e
    return filepath

def is_instagram_url(url):
    return 'instagram.com' in url

def is_twitter_url(url):
    return 'twitter.com' in url or 'x.com' in url

def get_instagram_info_data(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('description', 'Instagram Video')[:50] if info.get('description') else 'Instagram Video',
            'author': info.get('uploader', 'Instagram User'),
            'length': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'views': info.get('view_count', 0)
        }

def get_twitter_info_data(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('description', 'Twitter Video')[:80] if info.get('description') else 'Twitter Video',
            'author': info.get('uploader', 'Twitter User'),
            'length': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'views': info.get('view_count', 0)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_info', methods=['POST'])
def get_info():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Nenhum dado recebido'}), 400
            
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
        
        if is_instagram_url(url):
            info = get_instagram_info_data(url)
            return jsonify(info)
        
        if is_twitter_url(url):
            info = get_twitter_info_data(url)
            return jsonify(info)

        yt = YouTube(logging=False)
        yt.extract(url)
        yt.analyze_information()
        
        thumbnail = ""
        if yt.information.thumbnails:
            thumbnail = yt.information.thumbnails[0]

        return jsonify({
            'title': yt.information.title,
            'author': yt.information.channel_name,
            'length': yt.information.duration,
            'thumbnail': thumbnail,
            'views': yt.information.view_count
        })
    except Exception as e:
        print(f"Error getting info: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/progress/<download_id>')
def progress(download_id):
    def generate():
        while True:
            if download_id in download_progress:
                data = download_progress[download_id]
                yield f"data: {json.dumps(data)}\n\n"
                if data['status'] in ['completed', 'error']:
                    break
            else:
                yield f"data: {json.dumps({'status': 'waiting', 'percent': 0, 'message': 'Aguardando início...'})}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download', methods=['POST'])
def download():
    download_id = None
    try:
        if request.is_json:
            data = request.get_json()
            url = data.get('url')
            format_type = data.get('format', 'video')
            download_id = data.get('download_id')
        else:
            url = request.form.get('url')
            format_type = request.form.get('format', 'video')
            download_id = request.form.get('download_id')
        
        if download_id:
            download_progress[download_id] = {
                'status': 'starting',
                'percent': 0,
                'message': 'Iniciando extração...'
            }

        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
            
        download_url = None
        ext = 'mp4'
        mime = 'video/mp4'
        video_title = "video_download"

        if is_instagram_url(url):
            if download_id:
                download_progress[download_id]['message'] = 'Processando Instagram...'
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                download_url = info.get('url')
                ext = info.get('ext', 'mp4')
                video_title = info.get('description', 'instagram_video')[:50] if info.get('description') else 'instagram_video'
        elif is_twitter_url(url):
            if download_id:
                download_progress[download_id]['message'] = 'Processando Twitter/X...'
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                download_url = info.get('url')
                ext = info.get('ext', 'mp4')
                video_title = info.get('description', 'twitter_video')[:80] if info.get('description') else 'twitter_video'
        else:
            yt = YouTube(logging=False)
            yt.extract(url)
            yt.analyze_information()
            video_title = yt.information.title or "video_download"
            
            if format_type == 'audio':
                if download_id:
                    download_progress[download_id]['message'] = 'Analisando streams de áudio...'
                yt.analyze_audio_streams(preferred_language=["pt-BR", "source", "all"])
                if yt.best_audio_stream:
                    download_url = yt.best_audio_stream.get('url')
                    ext = yt.best_audio_stream.get('extension', 'mp3')
                    if ext == 'webm':
                        mime = 'audio/webm'
                    elif ext == 'm4a':
                        mime = 'audio/mp4'
                    else:
                        mime = 'audio/mpeg'
            else:
                if download_id:
                    download_progress[download_id]['message'] = 'Analisando streams de vídeo...'
                
                progressive_url = None
                best_progressive_quality = 0
                
                for stream in yt._raw_youtube_streams:
                    vcodec = stream.get('vcodec')
                    acodec = stream.get('acodec')
                    url_stream = stream.get('url', '')
                    
                    if 'manifest.googlevideo.com' in url_stream or '.m3u8' in url_stream:
                        continue
                    
                    if vcodec != 'none' and acodec != 'none':
                        height = stream.get('height', 0) or 0
                        if height > best_progressive_quality:
                            best_progressive_quality = height
                            progressive_url = url_stream
                            ext = 'mp4' 
                
                if progressive_url:
                    download_url = progressive_url
                    mime = 'video/mp4'
                else:
                    yt.analyze_video_streams(preferred_resolution="all")
                    if yt.best_video_download_url:
                        download_url = yt.best_video_download_url
                        ext = yt.best_video_stream.get('extension', 'mp4')
                        mime = 'video/mp4'
            
        if not download_url:
            if download_id:
                download_progress[download_id] = {'status': 'error', 'message': 'Stream não encontrado'}
            return jsonify({'error': 'Stream não encontrado'}), 404
            
        safe_title = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        if not safe_title:
            safe_title = "video_download"
            
        filename = f"{safe_title}.{ext}"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        download_file_from_url(download_url, filepath, download_id)

        if download_id:
            download_progress[download_id] = {
                'status': 'completed',
                'percent': 100,
                'message': 'Download concluído! Enviando arquivo...'
            }

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=mime
        )

    except Exception as e:
        print(f"Error: {e}")
        if download_id:
            download_progress[download_id] = {
                'status': 'error',
                'percent': 0,
                'message': f'Erro: {str(e)}'
            }
        return jsonify({'error': str(e)}), 400


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '1.1.0'})

@app.route('/list-downloads')
def list_downloads():
    try:
        files = []
        for f in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'name': f,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'path': os.path.abspath(filepath)
                })
        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/delete-file', methods=['POST'])
def delete_file():
    try:
        data = request.get_json()
        filename = data.get('filename')
        if not filename:
            return jsonify({'error': 'Nome do arquivo não fornecido'}), 400
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)
            return jsonify({'success': True})
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    # Porta 54321 para compatibilidade com Electron
    port = int(os.environ.get('PORT', 54321))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='127.0.0.1', port=port)