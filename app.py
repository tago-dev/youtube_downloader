import os
from pytubefix import YouTube
from flask import Flask, request, send_file, render_template, jsonify
import re

app = Flask(__name__)

if not os.path.exists('downloads'):
    os.makedirs('downloads')

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
        
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        return jsonify({
            'title': yt.title,
            'author': yt.author,
            'length': yt.length,
            'thumbnail': yt.thumbnail_url,
            'views': yt.views
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    try:
        # Handle both JSON and Form data
        if request.is_json:
            data = request.get_json()
            url = data.get('url')
            format_type = data.get('format', 'video')
        else:
            url = request.form.get('url')
            format_type = request.form.get('format', 'video')
        
        if not url:
            return jsonify({'error': 'URL não fornecida'}), 400
            
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        if format_type == 'audio':
            stream = yt.streams.filter(only_audio=True).first()
            ext = 'mp3'
            mime = 'audio/mpeg'
        else:
            stream = yt.streams.get_highest_resolution()
            ext = 'mp4'
            mime = 'video/mp4'
            
        if not stream:
            return jsonify({'error': 'Stream não encontrado'}), 404
            
        # Download to temp file
        out_file = stream.download(output_path='downloads')
        
        # If audio, we might want to rename to mp3 (pytube downloads as mp4 usually for audio streams)
        # But for simplicity, we serve as is, browsers handle it. 
        # Ideally we would use ffmpeg to convert.
        # Let's just serve the file.
        
        filename = os.path.basename(out_file)
        new_filename = filename
        
        if format_type == 'audio':
            base, _ = os.path.splitext(out_file)
            new_file = base + '.mp3'
            os.rename(out_file, new_file)
            out_file = new_file
            new_filename = os.path.basename(new_file)

        return send_file(
            out_file,
            as_attachment=True,
            download_name=new_filename,
            mimetype=mime
        )

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)