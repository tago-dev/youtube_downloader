from streamsnapper import YouTube
import traceback

def reproduce_error():
    url = "https://www.youtube.com/shorts/Hz64qfzhf8s"
    print(f"Testing URL: {url}")

    try:
        yt = YouTube(logging=True)
        print("Extracting...")
        yt.extract(url)
        
        print("Analyzing video streams...")
        yt.analyze_video_streams(preferred_resolution="all")
        
        print("Analyzing audio streams...")
        yt.analyze_audio_streams(preferred_language=["pt-BR", "source", "all"])
        
        print(f"Title: {yt.information.title}")
        safe_title = "".join([c for c in yt.information.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        print(f"Safe title: {safe_title}")

        print("Done.")

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    reproduce_error()
