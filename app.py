import os
from streamsnapper import YouTube, SupportedCookieBrowser
import requests
from flask import Flask, request, send_file, render_template, jsonify, Response
import re
import json
import time

app = Flask(__name__)

download_progress = {}

if not os.path.exists('downloads'):
    os.makedirs('downloads')

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
            
        yt = YouTube(logging=False)
        yt.extract(url)
        yt.analyze_information()
        
        download_url = None
        ext = 'mp4'
        mime = 'video/mp4'
        
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
                url = stream.get('url', '')
                
                if 'manifest.googlevideo.com' in url or '.m3u8' in url:
                    continue
                
                if vcodec != 'none' and acodec != 'none':
                    height = stream.get('height', 0) or 0
                    if height > best_progressive_quality:
                        best_progressive_quality = height
                        progressive_url = url
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
            
        video_title = yt.information.title or "video_download"
        safe_title = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        if not safe_title:
            safe_title = "video_download"
            
        filename = f"{safe_title}.{ext}"
        filepath = os.path.join('downloads', filename)
        
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)