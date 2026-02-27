import json
import os
import threading
import time
import traceback
import uuid

import requests
import yt_dlp
from flask import Flask, Response, jsonify, render_template, request, send_file
from streamsnapper import YouTube

app = Flask(__name__)

# Diretórios da aplicação
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
DATA_DIR = os.path.join(BASE_DIR, "data")
QUEUE_STATE_FILE = os.path.join(DATA_DIR, "queue_state.json")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Progresso legado para endpoint /download direto
download_progress = {}


class CancelledDownload(Exception):
    pass


def now_ts():
    return int(time.time())


def sanitize_title(title):
    safe_title = "".join([c for c in (title or "") if c.isalnum() or c in (" ", "-", "_")]).rstrip()
    return safe_title or "video_download"


def ensure_unique_path(directory, filename):
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return candidate


def is_instagram_url(url):
    return "instagram.com" in (url or "")


def is_twitter_url(url):
    return "twitter.com" in (url or "") or "x.com" in (url or "")


def get_instagram_info_data(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("description", "Instagram Video")[:50] if info.get("description") else "Instagram Video",
            "author": info.get("uploader", "Instagram User"),
            "length": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "views": info.get("view_count", 0),
        }


def get_twitter_info_data(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("description", "Twitter Video")[:80] if info.get("description") else "Twitter Video",
            "author": info.get("uploader", "Twitter User"),
            "length": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "views": info.get("view_count", 0),
        }


def resolve_download_request(url, format_type="video", progress_callback=None, cancel_check=None):
    def update(msg, status="processing", percent=0):
        if progress_callback:
            progress_callback(percent=percent, message=msg, status=status)

    def check_cancel():
        if cancel_check:
            cancel_check()

    download_url = None
    ext = "mp4"
    mime = "video/mp4"
    video_title = "video_download"

    check_cancel()

    if is_instagram_url(url):
        update("Processando Instagram...", "processing", 0)
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get("url")
            ext = info.get("ext", "mp4")
            video_title = info.get("description", "instagram_video")[:50] if info.get("description") else "instagram_video"
    elif is_twitter_url(url):
        update("Processando Twitter/X...", "processing", 0)
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
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
            update("Analisando streams de vídeo...", "processing", 0)
            progressive_url = None
            best_progressive_quality = 0

            for stream in yt._raw_youtube_streams:
                check_cancel()
                vcodec = stream.get("vcodec")
                acodec = stream.get("acodec")
                url_stream = stream.get("url", "")

                if "manifest.googlevideo.com" in url_stream or ".m3u8" in url_stream:
                    continue

                if vcodec != "none" and acodec != "none":
                    height = stream.get("height", 0) or 0
                    if height > best_progressive_quality:
                        best_progressive_quality = height
                        progressive_url = url_stream
                        ext = "mp4"

            if progressive_url:
                download_url = progressive_url
                mime = "video/mp4"
            else:
                yt.analyze_video_streams(preferred_resolution="all")
                check_cancel()
                if yt.best_video_download_url:
                    download_url = yt.best_video_download_url
                    ext = yt.best_video_stream.get("extension", "mp4")
                    mime = "video/mp4"

    if not download_url:
        raise ValueError("Stream não encontrado")

    return {
        "download_url": download_url,
        "ext": ext,
        "mime": mime,
        "video_title": video_title,
    }


def download_file_from_url(url, filepath, download_id=None, progress_callback=None, cancel_check=None):
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if cancel_check:
                        cancel_check()

                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)

                    percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                    message = f"Baixando do YouTube: {percent:.1f}%"

                    if download_id:
                        download_progress[download_id] = {
                            "status": "downloading",
                            "percent": percent,
                            "message": message,
                        }

                    if progress_callback:
                        progress_callback(percent=percent, message=message, status="downloading")

        if download_id:
            download_progress[download_id] = {
                "status": "processing",
                "percent": 100,
                "message": "Processando arquivo...",
            }

        if progress_callback:
            progress_callback(percent=100, message="Processando arquivo...", status="processing")

    except CancelledDownload:
        raise
    except Exception as e:
        if download_id:
            download_progress[download_id] = {
                "status": "error",
                "percent": 0,
                "message": f"Erro: {str(e)}",
            }
        if progress_callback:
            progress_callback(percent=0, message=f"Erro: {str(e)}", status="error")
        raise e
    return filepath


class QueueManager:
    TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

    def __init__(self, state_file, download_dir):
        self.state_file = state_file
        self.download_dir = download_dir
        self.lock = threading.RLock()
        self.jobs = {}
        self.queue_order = []
        self.current_job_id = None
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True, name="queue-worker")
        self._load_state()

    def start(self):
        if not self.worker.is_alive():
            self.worker.start()

    def stop(self):
        self._stop_event.set()
        self._wake_event.set()

    def _public_job(self, job):
        queue_position = None
        if job["status"] == "queued":
            try:
                queue_position = self.queue_order.index(job["id"]) + 1
            except ValueError:
                queue_position = None
        return {
            "id": job["id"],
            "url": job["url"],
            "format": job["format"],
            "status": job["status"],
            "percent": job.get("percent", 0),
            "message": job.get("message", ""),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "filename": job.get("filename"),
            "filepath": job.get("filepath"),
            "error": job.get("error"),
            "queue_position": queue_position,
            "can_retry": job["status"] in {"failed", "cancelled"},
            "can_cancel": job["status"] in {"queued", "running"},
            "is_current": self.current_job_id == job["id"],
        }

    def stats(self):
        with self.lock:
            total = len(self.jobs)
            queued = sum(1 for j in self.jobs.values() if j["status"] == "queued")
            running = sum(1 for j in self.jobs.values() if j["status"] == "running")
            completed = sum(1 for j in self.jobs.values() if j["status"] == "completed")
            failed = sum(1 for j in self.jobs.values() if j["status"] == "failed")
            cancelled = sum(1 for j in self.jobs.values() if j["status"] == "cancelled")
            return {
                "total": total,
                "queued": queued,
                "running": running,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "current_job_id": self.current_job_id,
            }

    def list_jobs(self):
        with self.lock:
            ordered = sorted(self.jobs.values(), key=lambda x: x.get("created_at", 0), reverse=True)
            return [self._public_job(j) for j in ordered]

    def get_job(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return self._public_job(job)

    def enqueue(self, url, format_type):
        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "url": url,
            "format": format_type,
            "status": "queued",
            "percent": 0,
            "message": "Aguardando na fila...",
            "created_at": now_ts(),
            "updated_at": now_ts(),
            "filename": None,
            "filepath": None,
            "error": None,
            "cancel_requested": False,
        }
        with self.lock:
            self.jobs[job_id] = job
            self.queue_order.append(job_id)
            self._persist_state_locked()
        self._wake_event.set()
        return self.get_job(job_id)

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False, "Job não encontrado"

            if job["status"] == "queued":
                if job_id in self.queue_order:
                    self.queue_order.remove(job_id)
                job["status"] = "cancelled"
                job["percent"] = 0
                job["message"] = "Cancelado pelo usuário"
                job["updated_at"] = now_ts()
                self._persist_state_locked()
                return True, "Job cancelado"

            if job["status"] == "running":
                job["cancel_requested"] = True
                job["message"] = "Cancelamento solicitado..."
                job["updated_at"] = now_ts()
                self._persist_state_locked()
                return True, "Cancelamento solicitado"

            return False, "Job não pode ser cancelado nesse estado"

    def retry(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None, "Job não encontrado"
            if job["status"] not in {"failed", "cancelled"}:
                return None, "Somente jobs com falha/cancelados podem ser reenfileirados"
            url = job["url"]
            format_type = job["format"]
        return self.enqueue(url, format_type), None

    def reorder(self, job_id, new_position):
        with self.lock:
            if job_id not in self.queue_order:
                return False, "Job não está na fila pendente"
            self.queue_order.remove(job_id)
            bounded = max(0, min(int(new_position), len(self.queue_order)))
            self.queue_order.insert(bounded, job_id)
            self._persist_state_locked()
            return True, "Fila reordenada"

    def _load_state(self):
        with self.lock:
            if not os.path.exists(self.state_file):
                return
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)

                jobs = payload.get("jobs", {})
                queue_order = payload.get("queue_order", [])

                self.jobs = {}
                for job_id, job in jobs.items():
                    if not isinstance(job, dict):
                        continue
                    restored = {
                        "id": job_id,
                        "url": job.get("url"),
                        "format": job.get("format", "video"),
                        "status": job.get("status", "queued"),
                        "percent": job.get("percent", 0),
                        "message": job.get("message", "Aguardando na fila..."),
                        "created_at": job.get("created_at", now_ts()),
                        "updated_at": now_ts(),
                        "filename": job.get("filename"),
                        "filepath": job.get("filepath"),
                        "error": job.get("error"),
                        "cancel_requested": False,
                    }

                    if restored["status"] in {"running", "queued", "starting", "processing", "downloading"}:
                        restored["status"] = "queued"
                        restored["message"] = "Retomado após reinício do app"
                        restored["percent"] = 0

                    self.jobs[job_id] = restored

                self.queue_order = [jid for jid in queue_order if jid in self.jobs and self.jobs[jid]["status"] == "queued"]
                for jid, job in self.jobs.items():
                    if job["status"] == "queued" and jid not in self.queue_order:
                        self.queue_order.append(jid)

            except Exception:
                print("Erro ao restaurar fila persistida:")
                traceback.print_exc()

    def _persist_state_locked(self):
        payload = {
            "jobs": {},
            "queue_order": self.queue_order,
            "saved_at": now_ts(),
        }

        for job_id, job in self.jobs.items():
            payload["jobs"][job_id] = {
                "url": job.get("url"),
                "format": job.get("format"),
                "status": job.get("status"),
                "percent": job.get("percent"),
                "message": job.get("message"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "filename": job.get("filename"),
                "filepath": job.get("filepath"),
                "error": job.get("error"),
            }

        temp_path = f"{self.state_file}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.state_file)

    def _update_job_progress(self, job_id, percent, message, status=None):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job["percent"] = max(0, min(100, float(percent)))
            job["message"] = message
            if status:
                job["status"] = status
            job["updated_at"] = now_ts()
            self._persist_state_locked()

    def _cancel_check_factory(self, job_id):
        def _check():
            with self.lock:
                job = self.jobs.get(job_id)
                if not job:
                    raise CancelledDownload("Job removido")
                if job.get("cancel_requested"):
                    raise CancelledDownload("Cancelado pelo usuário")

        return _check

    def _worker_loop(self):
        while not self._stop_event.is_set():
            job_id = None
            with self.lock:
                while self.queue_order:
                    candidate = self.queue_order.pop(0)
                    job = self.jobs.get(candidate)
                    if job and job["status"] == "queued":
                        job_id = candidate
                        self.current_job_id = job_id
                        job["status"] = "running"
                        job["message"] = "Iniciando extração..."
                        job["percent"] = 0
                        job["updated_at"] = now_ts()
                        self._persist_state_locked()
                        break

                if not job_id:
                    self.current_job_id = None

            if not job_id:
                self._wake_event.wait(timeout=1.0)
                self._wake_event.clear()
                continue

            self._process_job(job_id)

            with self.lock:
                self.current_job_id = None
                self._persist_state_locked()

    def _process_job(self, job_id):
        tmp_path = None
        try:
            with self.lock:
                job = self.jobs.get(job_id)
                if not job:
                    return
                url = job["url"]
                format_type = job["format"]

            cancel_check = self._cancel_check_factory(job_id)
            source = resolve_download_request(
                url=url,
                format_type=format_type,
                progress_callback=lambda percent, message, status: self._update_job_progress(
                    job_id, percent=percent, message=message, status="running"
                ),
                cancel_check=cancel_check,
            )

            safe_title = sanitize_title(source["video_title"])
            filename = f"{safe_title}.{source['ext']}"
            final_path = ensure_unique_path(self.download_dir, filename)
            tmp_path = f"{final_path}.part"

            download_file_from_url(
                source["download_url"],
                tmp_path,
                progress_callback=lambda percent, message, status: self._update_job_progress(
                    job_id, percent=percent, message=message, status="running"
                ),
                cancel_check=cancel_check,
            )

            os.replace(tmp_path, final_path)
            tmp_path = None

            with self.lock:
                job = self.jobs.get(job_id)
                if not job:
                    return
                job["status"] = "completed"
                job["percent"] = 100
                job["message"] = "Download concluído!"
                job["filename"] = os.path.basename(final_path)
                job["filepath"] = os.path.abspath(final_path)
                job["error"] = None
                job["updated_at"] = now_ts()
                self._persist_state_locked()

        except CancelledDownload as e:
            with self.lock:
                job = self.jobs.get(job_id)
                if job:
                    job["status"] = "cancelled"
                    job["message"] = str(e) or "Cancelado pelo usuário"
                    job["error"] = str(e)
                    job["updated_at"] = now_ts()
                    self._persist_state_locked()
        except Exception as e:
            with self.lock:
                job = self.jobs.get(job_id)
                if job:
                    job["status"] = "failed"
                    job["message"] = f"Erro: {str(e)}"
                    job["error"] = str(e)
                    job["updated_at"] = now_ts()
                    self._persist_state_locked()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


queue_manager = QueueManager(QUEUE_STATE_FILE, DOWNLOAD_DIR)
queue_manager.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_info", methods=["POST"])
def get_info():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400

        url = data.get("url")
        if not url:
            return jsonify({"error": "URL não fornecida"}), 400

        if is_instagram_url(url):
            return jsonify(get_instagram_info_data(url))

        if is_twitter_url(url):
            return jsonify(get_twitter_info_data(url))

        yt = YouTube(logging=False)
        yt.extract(url)
        yt.analyze_information()

        thumbnail = ""
        if yt.information.thumbnails:
            thumbnail = yt.information.thumbnails[0]

        return jsonify(
            {
                "title": yt.information.title,
                "author": yt.information.channel_name,
                "length": yt.information.duration,
                "thumbnail": thumbnail,
                "views": yt.information.view_count,
            }
        )
    except Exception as e:
        print(f"Error getting info: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/progress/<download_id>")
def progress(download_id):
    def generate():
        while True:
            if download_id in download_progress:
                data = download_progress[download_id]
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in ["completed", "error"]:
                    break
            else:
                yield f"data: {json.dumps({'status': 'waiting', 'percent': 0, 'message': 'Aguardando início...'})}\n\n"
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/queue/events")
def queue_events():
    def generate():
        while True:
            payload = {"jobs": queue_manager.list_jobs(), "stats": queue_manager.stats(), "ts": now_ts()}
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/queue/progress/<job_id>")
def queue_progress(job_id):
    def generate():
        while True:
            job = queue_manager.get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job não encontrado'})}\n\n"
                break

            yield f"data: {json.dumps(job)}\n\n"
            if job["status"] in QueueManager.TERMINAL_STATUSES:
                break
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/queue/enqueue", methods=["POST"])
def queue_enqueue():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado recebido"}), 400

        url = data.get("url")
        format_type = data.get("format", "video")
        if not url:
            return jsonify({"error": "URL não fornecida"}), 400
        if format_type not in {"video", "audio"}:
            return jsonify({"error": "Formato inválido"}), 400

        job = queue_manager.enqueue(url, format_type)
        return jsonify({"job": job, "stats": queue_manager.stats()}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/queue/jobs")
def queue_jobs():
    try:
        return jsonify({"jobs": queue_manager.list_jobs(), "stats": queue_manager.stats()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/queue/cancel", methods=["POST"])
def queue_cancel():
    try:
        data = request.get_json()
        job_id = (data or {}).get("job_id")
        if not job_id:
            return jsonify({"error": "job_id não fornecido"}), 400

        ok, message = queue_manager.cancel(job_id)
        if not ok:
            return jsonify({"error": message}), 400
        return jsonify({"success": True, "message": message, "job": queue_manager.get_job(job_id)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/queue/retry", methods=["POST"])
def queue_retry():
    try:
        data = request.get_json()
        job_id = (data or {}).get("job_id")
        if not job_id:
            return jsonify({"error": "job_id não fornecido"}), 400

        job, error = queue_manager.retry(job_id)
        if error:
            return jsonify({"error": error}), 400
        return jsonify({"success": True, "job": job, "stats": queue_manager.stats()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/queue/reorder", methods=["POST"])
def queue_reorder():
    try:
        data = request.get_json()
        job_id = (data or {}).get("job_id")
        new_position = (data or {}).get("position")

        if not job_id or new_position is None:
            return jsonify({"error": "job_id e position são obrigatórios"}), 400

        ok, message = queue_manager.reorder(job_id, int(new_position))
        if not ok:
            return jsonify({"error": message}), 400
        return jsonify({"success": True, "message": message, "stats": queue_manager.stats()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/queue/file/<job_id>")
def queue_file(job_id):
    job = queue_manager.get_job(job_id)
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404
    if job["status"] != "completed":
        return jsonify({"error": "Arquivo ainda não está pronto"}), 400
    if not job.get("filepath") or not os.path.exists(job["filepath"]):
        return jsonify({"error": "Arquivo não encontrado no disco"}), 404
    mimetype = "audio/mpeg" if job.get("format") == "audio" else "video/mp4"
    return send_file(job["filepath"], as_attachment=True, download_name=job.get("filename"), mimetype=mimetype)


@app.route("/download", methods=["POST"])
def download():
    download_id = None
    try:
        if request.is_json:
            data = request.get_json()
            url = data.get("url")
            format_type = data.get("format", "video")
            download_id = data.get("download_id")
        else:
            url = request.form.get("url")
            format_type = request.form.get("format", "video")
            download_id = request.form.get("download_id")

        if download_id:
            download_progress[download_id] = {
                "status": "starting",
                "percent": 0,
                "message": "Iniciando extração...",
            }

        if not url:
            return jsonify({"error": "URL não fornecida"}), 400

        source = resolve_download_request(url=url, format_type=format_type)
        safe_title = sanitize_title(source["video_title"])
        filename = f"{safe_title}.{source['ext']}"
        filepath = ensure_unique_path(DOWNLOAD_DIR, filename)

        download_file_from_url(source["download_url"], filepath, download_id=download_id)

        if download_id:
            download_progress[download_id] = {
                "status": "completed",
                "percent": 100,
                "message": "Download concluído! Enviando arquivo...",
            }

        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath), mimetype=source["mime"])

    except Exception as e:
        print(f"Error: {e}")
        if download_id:
            download_progress[download_id] = {
                "status": "error",
                "percent": 0,
                "message": f"Erro: {str(e)}",
            }
        return jsonify({"error": str(e)}), 400


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "2.0.0"})


@app.route("/list-downloads")
def list_downloads():
    try:
        files = []
        for f in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append(
                    {
                        "name": f,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "path": os.path.abspath(filepath),
                    }
                )
        files.sort(key=lambda x: x["modified"], reverse=True)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/delete-file", methods=["POST"])
def delete_file():
    try:
        data = request.get_json()
        filename = data.get("filename")
        if not filename:
            return jsonify({"error": "Nome do arquivo não fornecido"}), 400
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)
            return jsonify({"success": True})
        return jsonify({"error": "Arquivo não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    # Porta 54321 para compatibilidade com Electron
    port = int(os.environ.get("PORT", 54321))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="127.0.0.1", port=port)