from __future__ import annotations

import os
import shutil
import time
from typing import Any, Callable

import requests
import yt_dlp
from streamsnapper import YouTube

ProgressCallback = Callable[[float, str, str], None]
CancelCheck = Callable[[], None]


class CancelledDownload(Exception):
    pass


def now_ts() -> int:
    return int(time.time())


def sanitize_title(title: str | None) -> str:
    safe_title = "".join([c for c in (title or "") if c.isalnum() or c in (" ", "-", "_")]).rstrip()
    return safe_title or "media_download"


def ensure_unique_path(directory: str | os.PathLike[str], filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return candidate


def is_instagram_url(url: str | None) -> bool:
    return "instagram.com" in (url or "")


def is_twitter_url(url: str | None) -> bool:
    return "twitter.com" in (url or "") or "x.com" in (url or "")


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _extract_with_ytdlp(url: str, format_selector: str = "best") -> dict[str, Any]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": format_selector,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def get_instagram_info_data(url: str) -> dict[str, Any]:
    info = _extract_with_ytdlp(url)
    return {
        "title": info.get("description", "Instagram Video")[:50] if info.get("description") else "Instagram Video",
        "author": info.get("uploader", "Instagram User"),
        "length": info.get("duration", 0),
        "thumbnail": info.get("thumbnail", ""),
        "views": info.get("view_count", 0),
        "source": "instagram",
    }


def get_twitter_info_data(url: str) -> dict[str, Any]:
    info = _extract_with_ytdlp(url)
    return {
        "title": info.get("description", "Twitter Video")[:80] if info.get("description") else "Twitter Video",
        "author": info.get("uploader", "Twitter User"),
        "length": info.get("duration", 0),
        "thumbnail": info.get("thumbnail", ""),
        "views": info.get("view_count", 0),
        "source": "twitter",
    }


def get_youtube_info_data(url: str) -> dict[str, Any]:
    yt = YouTube(logging=False)
    yt.extract(url)
    yt.analyze_information()

    thumbnail = ""
    if yt.information.thumbnails:
        thumbnail = yt.information.thumbnails[0]

    return {
        "title": yt.information.title,
        "author": yt.information.channel_name,
        "length": yt.information.duration,
        "thumbnail": thumbnail,
        "views": yt.information.view_count,
        "source": "youtube",
    }


def get_media_info_data(url: str) -> dict[str, Any]:
    if is_instagram_url(url):
        return get_instagram_info_data(url)
    if is_twitter_url(url):
        return get_twitter_info_data(url)
    return get_youtube_info_data(url)


def _ensure_unique_stem(directory: str | os.PathLike[str], stem: str) -> str:
    candidate = os.path.join(directory, stem)
    counter = 1
    while os.path.exists(candidate) or any(
        name == stem or name.startswith(f"{stem}.") or name.startswith(f"{stem}_")
        for name in os.listdir(directory)
    ):
        candidate = os.path.join(directory, f"{stem}_{counter}")
        counter += 1
        stem = os.path.basename(candidate)
    return candidate


def _best_youtube_video_selector() -> tuple[str, str | None]:
    if has_ffmpeg():
        return ("bestvideo*+bestaudio/bestvideo+bestaudio/best", "mp4")
    return ("best[acodec!=none][vcodec!=none]/best", None)


def resolve_download_request(
    url: str,
    format_type: str = "video",
    progress_callback: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict[str, str]:
    def update(message: str, status: str = "processing", percent: float = 0) -> None:
        if progress_callback:
            progress_callback(percent, message, status)

    def check_cancel() -> None:
        if cancel_check:
            cancel_check()

    download_url = None
    ext = "mp4"
    mime = "video/mp4"
    video_title = "media_download"

    check_cancel()

    if is_instagram_url(url):
        update("Processando Instagram...", "processing", 0)
        info = _extract_with_ytdlp(url)
        download_url = info.get("url")
        ext = info.get("ext", "mp4")
        video_title = info.get("description", "instagram_video")[:50] if info.get("description") else "instagram_video"
    elif is_twitter_url(url):
        update("Processando Twitter/X...", "processing", 0)
        info = _extract_with_ytdlp(url)
        download_url = info.get("url")
        ext = info.get("ext", "mp4")
        video_title = info.get("description", "twitter_video")[:80] if info.get("description") else "twitter_video"
    else:
        yt = YouTube(logging=False)
        yt.extract(url)
        yt.analyze_information()
        video_title = yt.information.title or "video_download"

        if format_type == "audio":
            update("Analisando streams de áudio...", "processing", 0)
            yt.analyze_audio_streams(preferred_language=["pt-BR", "source", "all"])
            check_cancel()
            if yt.best_audio_stream:
                download_url = yt.best_audio_stream.get("url")
                ext = yt.best_audio_stream.get("extension", "mp3")
                if ext == "webm":
                    mime = "audio/webm"
                elif ext == "m4a":
                    mime = "audio/mp4"
                else:
                    mime = "audio/mpeg"
        else:
            update("Selecionando a melhor qualidade de vídeo...", "processing", 0)
            format_selector, preferred_ext = _best_youtube_video_selector()
            return {
                "download_url": url,
                "ext": preferred_ext or "mp4",
                "mime": "video/mp4",
                "video_title": video_title,
                "strategy": "ytdlp",
                "format_selector": format_selector,
                "preferred_ext": preferred_ext or "",
            }

    if not download_url:
        raise ValueError("Stream não encontrado")

    return {
        "download_url": download_url,
        "ext": ext,
        "mime": mime,
        "video_title": video_title,
        "strategy": "direct",
    }


def download_file_from_url(
    url: str,
    filepath: str,
    progress_callback: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> str:
    try:
        with requests.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as file_obj:
                for chunk in response.iter_content(chunk_size=8192):
                    if cancel_check:
                        cancel_check()

                    if not chunk:
                        continue

                    file_obj.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                    message = f"Baixando: {percent:.1f}%"

                    if progress_callback:
                        progress_callback(percent, message, "downloading")

        if progress_callback:
            progress_callback(100, "Processando arquivo...", "processing")
    except CancelledDownload:
        raise
    except Exception as exc:
        if progress_callback:
            progress_callback(0, f"Erro: {exc}", "error")
        raise
    return filepath


def download_with_ytdlp(
    url: str,
    output_dir: str | os.PathLike[str],
    title: str,
    format_selector: str,
    progress_callback: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
    preferred_ext: str | None = None,
) -> str:
    base_stem = sanitize_title(title)
    output_base = _ensure_unique_stem(output_dir, base_stem)
    outtmpl = f"{output_base}.%(ext)s"

    def hook(data: dict[str, Any]) -> None:
        if cancel_check:
            cancel_check()

        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            percent = (downloaded / total) * 100 if total else 0
            speed = data.get("speed")
            speed_label = ""
            if speed:
                speed_label = f" ({speed / 1024 / 1024:.1f} MB/s)"
            if progress_callback:
                progress_callback(percent, f"Baixando na melhor qualidade: {percent:.1f}%{speed_label}", "downloading")
        elif status == "finished" and progress_callback:
            progress_callback(100, "Finalizando arquivo...", "processing")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": format_selector,
        "outtmpl": {"default": outtmpl},
        "noplaylist": True,
        "progress_hooks": [hook],
    }
    if preferred_ext:
        ydl_opts["merge_output_format"] = preferred_ext

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            candidates: list[str] = []

            filename = info.get("_filename")
            if isinstance(filename, str):
                candidates.append(filename)

            prepared = ydl.prepare_filename(info)
            if isinstance(prepared, str):
                candidates.append(prepared)
                if preferred_ext:
                    candidates.append(f"{os.path.splitext(prepared)[0]}.{preferred_ext}")

            requested_downloads = info.get("requested_downloads") or []
            for item in requested_downloads:
                filepath = item.get("filepath")
                if isinstance(filepath, str):
                    candidates.append(filepath)

            for candidate in candidates:
                if candidate and os.path.exists(candidate):
                    return candidate

        directory = os.fspath(output_dir)
        prefix = os.path.basename(output_base)
        recent_matches = [
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if name == prefix or name.startswith(f"{prefix}.") or name.startswith(f"{prefix}_")
        ]
        if recent_matches:
            recent_matches.sort(key=os.path.getmtime, reverse=True)
            return recent_matches[0]
    except CancelledDownload:
        raise
    except Exception as exc:
        if "Cancelado pelo usuário" in str(exc):
            raise CancelledDownload("Cancelado pelo usuário") from exc
        raise

    raise ValueError("Não foi possível localizar o arquivo baixado")
