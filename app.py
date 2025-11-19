import os
from streamsnapper import YouTube, SupportedCookieBrowser
import requests
from flask import Flask, request, send_file, render_template, jsonify
import re

app = Flask(__name__)

if not os.path.exists('downloads'):
    os.makedirs('downloads')

def download_file_from_url(url, filepath):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
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

@app.route('/download', methods=['POST'])
def download():
    try:
        if request.is_json:
            data = request.get_json()
            url = data.get('url')
            format_type = data.get('format', 'video')
        else:
            url = request.form.get('url')
            format_type = request.form.get('format', 'video')
        
        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
            
        yt = YouTube(logging=False)
        yt.extract(url)
        
        download_url = None
        ext = 'mp4'
        mime = 'video/mp4'
        
        if format_type == 'audio':
            yt.analyze_audio_streams(preferred_language=["pt-BR", "source", "all"])
            if yt.best_audio_download_url:
                download_url = yt.best_audio_download_url
                ext = 'mp3'
                mime = 'audio/mpeg'
        else:
            yt.analyze_video_streams(preferred_resolution="all")
            if yt.best_video_download_url:
                download_url = yt.best_video_download_url
                ext = 'mp4'
                mime = 'video/mp4'
            
        if not download_url:
            return jsonify({'error': 'Stream não encontrado'}), 404
            
        safe_title = "".join([c for c in yt.information.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{safe_title}.{ext}"
        filepath = os.path.join('downloads', filename)
        
        download_file_from_url(download_url, filepath)

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=mime
        )

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)