from __future__ import annotations

import json
import os
import threading
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable

from .core import CancelledDownload, download_file_from_url, download_with_ytdlp, ensure_unique_path, now_ts, resolve_download_request, sanitize_title

QueueListener = Callable[[dict[str, Any]], None]


class QueueManager:
    TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

    def __init__(self, state_file: str | Path, download_dir: str | Path):
        self.state_file = Path(state_file)
        self.download_dir = Path(download_dir)
        self.lock = threading.RLock()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.queue_order: list[str] = []
        self.current_job_id: str | None = None
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._listeners: list[QueueListener] = []
        self.worker = threading.Thread(target=self._worker_loop, daemon=True, name="queue-worker")
        self._load_state()

    def start(self) -> None:
        if not self.worker.is_alive():
            self.worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def subscribe(self, callback: QueueListener, emit_initial: bool = True) -> None:
        payload = None
        with self.lock:
            self._listeners.append(callback)
            if emit_initial:
                payload = self._snapshot_locked()
        if payload is not None:
            self._notify_listener(callback, payload)

    def _notify_listener(self, callback: QueueListener, payload: dict[str, Any]) -> None:
        try:
            callback(payload)
        except Exception:
            traceback.print_exc()

    def _notify_listeners(self, payload: dict[str, Any] | None = None) -> None:
        with self.lock:
            snapshot = payload or self._snapshot_locked()
            listeners = list(self._listeners)
        for callback in listeners:
            self._notify_listener(callback, snapshot)

    def _public_job(self, job: dict[str, Any]) -> dict[str, Any]:
        queue_position = None
        if job["status"] == "queued":
            try:
                queue_position = self.queue_order.index(job["id"]) + 1
            except ValueError:
                queue_position = None

        return {
            "id": job["id"],
            "url": job["url"],
            "title": job.get("title"),
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

    def _snapshot_locked(self) -> dict[str, Any]:
        ordered = sorted(self.jobs.values(), key=lambda item: item.get("created_at", 0), reverse=True)
        jobs = [self._public_job(job) for job in ordered]
        total = len(self.jobs)
        queued = sum(1 for job in self.jobs.values() if job["status"] == "queued")
        running = sum(1 for job in self.jobs.values() if job["status"] == "running")
        completed = sum(1 for job in self.jobs.values() if job["status"] == "completed")
        failed = sum(1 for job in self.jobs.values() if job["status"] == "failed")
        cancelled = sum(1 for job in self.jobs.values() if job["status"] == "cancelled")
        return {
            "jobs": jobs,
            "stats": {
                "total": total,
                "queued": queued,
                "running": running,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "current_job_id": self.current_job_id,
            },
            "ts": now_ts(),
        }

    def stats(self) -> dict[str, Any]:
        with self.lock:
            return self._snapshot_locked()["stats"]

    def list_jobs(self) -> list[dict[str, Any]]:
        with self.lock:
            return self._snapshot_locked()["jobs"]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return self._public_job(job)

    def enqueue(self, url: str, format_type: str) -> dict[str, Any]:
        if format_type not in {"video", "audio"}:
            raise ValueError("Formato inválido")

        job_id = uuid.uuid4().hex
        with self.lock:
            self.jobs[job_id] = {
                "id": job_id,
                "url": url,
                "title": None,
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
            self.queue_order.append(job_id)
            job = self._public_job(self.jobs[job_id])
            self._persist_state_locked()
        self._wake_event.set()
        self._notify_listeners()
        return job

    def cancel(self, job_id: str) -> tuple[bool, str]:
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
            elif job["status"] == "running":
                job["cancel_requested"] = True
                job["message"] = "Cancelamento solicitado..."
                job["updated_at"] = now_ts()
                self._persist_state_locked()
            else:
                return False, "Job não pode ser cancelado nesse estado"

        self._notify_listeners()
        return True, "Cancelamento solicitado" if job["status"] == "running" else "Job cancelado"

    def retry(self, job_id: str) -> tuple[dict[str, Any] | None, str | None]:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None, "Job não encontrado"
            if job["status"] not in {"failed", "cancelled"}:
                return None, "Somente jobs com falha/cancelados podem ser reenfileirados"
            url = job["url"]
            format_type = job["format"]
        return self.enqueue(url, format_type), None

    def _load_state(self) -> None:
        with self.lock:
            if not self.state_file.exists():
                return
            try:
                payload = json.loads(self.state_file.read_text(encoding="utf-8"))
                jobs = payload.get("jobs", {})
                queue_order = payload.get("queue_order", [])

                self.jobs = {}
                for job_id, job in jobs.items():
                    if not isinstance(job, dict):
                        continue
                    restored = {
                        "id": job_id,
                        "url": job.get("url"),
                        "title": job.get("title"),
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

                self.queue_order = [job_id for job_id in queue_order if job_id in self.jobs and self.jobs[job_id]["status"] == "queued"]
                for job_id, job in self.jobs.items():
                    if job["status"] == "queued" and job_id not in self.queue_order:
                        self.queue_order.append(job_id)
            except Exception:
                print("Erro ao restaurar fila persistida:")
                traceback.print_exc()

    def _persist_state_locked(self) -> None:
        payload = {
            "jobs": {},
            "queue_order": self.queue_order,
            "saved_at": now_ts(),
        }

        for job_id, job in self.jobs.items():
            payload["jobs"][job_id] = {
                "url": job.get("url"),
                "title": job.get("title"),
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

        temp_path = self.state_file.with_suffix(f"{self.state_file.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, self.state_file)

    def _update_job_progress(self, job_id: str, percent: float, message: str, status: str | None = None) -> None:
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
        self._notify_listeners()

    def _cancel_check_factory(self, job_id: str):
        def _check() -> None:
            with self.lock:
                job = self.jobs.get(job_id)
                if not job:
                    raise CancelledDownload("Job removido")
                if job.get("cancel_requested"):
                    raise CancelledDownload("Cancelado pelo usuário")

        return _check

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            job_id = None
            should_notify = False

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
                        should_notify = True
                        break

                if not job_id:
                    self.current_job_id = None

            if should_notify:
                self._notify_listeners()

            if not job_id:
                self._wake_event.wait(timeout=1.0)
                self._wake_event.clear()
                continue

            self._process_job(job_id)

            with self.lock:
                self.current_job_id = None
                self._persist_state_locked()
            self._notify_listeners()

    def _process_job(self, job_id: str) -> None:
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

            with self.lock:
                job = self.jobs.get(job_id)
                if job:
                    job["title"] = source["video_title"]
                    job["updated_at"] = now_ts()
                    self._persist_state_locked()
            self._notify_listeners()

            if source.get("strategy") == "ytdlp":
                final_path = download_with_ytdlp(
                    url=source["download_url"],
                    output_dir=self.download_dir,
                    title=source["video_title"],
                    format_selector=source["format_selector"],
                    progress_callback=lambda percent, message, status: self._update_job_progress(
                        job_id, percent=percent, message=message, status="running"
                    ),
                    cancel_check=cancel_check,
                    preferred_ext=source.get("preferred_ext") or None,
                )
            else:
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
            self._notify_listeners()
        except CancelledDownload as exc:
            with self.lock:
                job = self.jobs.get(job_id)
                if job:
                    job["status"] = "cancelled"
                    job["message"] = str(exc) or "Cancelado pelo usuário"
                    job["error"] = str(exc)
                    job["updated_at"] = now_ts()
                    self._persist_state_locked()
            self._notify_listeners()
        except Exception as exc:
            with self.lock:
                job = self.jobs.get(job_id)
                if job:
                    job["status"] = "failed"
                    job["message"] = f"Erro: {exc}"
                    job["error"] = str(exc)
                    job["updated_at"] = now_ts()
                    self._persist_state_locked()
            self._notify_listeners()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
