from streamsnapper import YouTube
import json

def check_urls():
    url = "https://www.youtube.com/shorts/Hz64qfzhf8s"
    yt = YouTube(logging=True)
    yt.extract(url)
    
    print("Checking progressive streams...")
    for stream in yt._raw_youtube_streams:
        vcodec = stream.get('vcodec')
        acodec = stream.get('acodec')
        
        if vcodec != 'none' and acodec != 'none':
            url = stream.get('url', '')
            is_manifest = 'manifest.googlevideo.com' in url or '.m3u8' in url
            print(f"Res: {stream.get('height')} | Manifest: {is_manifest} | URL start: {url[:50]}...")

if __name__ == "__main__":
    check_urls()
