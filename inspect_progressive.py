from streamsnapper import YouTube
import json

def inspect_raw_streams():
    url = "https://www.youtube.com/shorts/Hz64qfzhf8s"
    yt = YouTube(logging=True)
    yt.extract(url)
    
    print(f"Total raw streams: {len(yt._raw_youtube_streams)}")
    
    progressive_streams = []
    for stream in yt._raw_youtube_streams:
        itag = stream.get('format_id')
        acodec = stream.get('acodec')
        vcodec = stream.get('vcodec')
        
        if acodec != 'none' and vcodec != 'none':
            progressive_streams.append({
                'itag': itag,
                'res': stream.get('height'),
                'acodec': acodec,
                'vcodec': vcodec,
                'url': stream.get('url')
            })
            
    print("Progressive Streams found:")
    print(json.dumps(progressive_streams, indent=2))

if __name__ == "__main__":
    inspect_raw_streams()
