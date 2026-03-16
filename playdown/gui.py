from __future__ import annotations

import io
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import customtkinter as ctk
import requests
from PIL import Image
import tkinter as tk
from tkinter import messagebox

from .core import get_media_info_data, has_ffmpeg
from .paths import AppPaths, create_app_paths
from .queue_manager import QueueManager


def format_duration(total_seconds: int | None) -> str:
    if not total_seconds:
        return "N/A"
    total_seconds = int(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_views(views: int | None) -> str:
    if not views:
        return "N/A"
    return f"{int(views):,}".replace(",", ".")


def open_path(path: str | Path) -> None:
    target = str(path)
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", target])
    elif os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", target])


class PlaydownApp(ctk.CTk):
    def __init__(self, paths: AppPaths):
        super().__init__()
        self.paths = paths
        self.queue_manager = QueueManager(paths.queue_state_file, paths.downloads_dir)
        self.queue_events: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self.preview_events: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self.preview_request_id = 0
        self.thumbnail_image = None

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Playdown")
        self.geometry("1180x760")
        self.minsize(980, 700)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value="video")
        self.feedback_var = tk.StringVar(value="Cole uma URL para analisar ou adicionar à fila.")
        self.current_job_var = tk.StringVar(value="Fila ociosa")
        self.current_message_var = tk.StringVar(value="Nenhum download em andamento.")
        self.stats_var = tk.StringVar(value="0 itens na fila")
        self.preview_title_var = tk.StringVar(value="Nenhuma mídia carregada")
        self.preview_author_var = tk.StringVar(value="-")
        self.preview_meta_var = tk.StringVar(value="Duração: N/A  •  Views: N/A")
        self.preview_source_var = tk.StringVar(value="Origem: -")

        self._build_layout()

        self.queue_manager.subscribe(self._push_queue_state, emit_initial=True)
        self.queue_manager.start()
        self.after(150, self._process_ui_events)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=16)
        header.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Playdown", font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 4), sticky="w"
        )
        ctk.CTkLabel(
            header,
            text="Downloader desktop nativo em Python com fila persistente.",
            text_color=("gray30", "gray70"),
        ).grid(row=1, column=0, padx=20, pady=(0, 18), sticky="w")
        ctk.CTkButton(header, text="Abrir pasta de downloads", command=self._open_downloads_folder).grid(
            row=0, column=1, rowspan=2, padx=20, pady=18, sticky="e"
        )

        left_panel = ctk.CTkFrame(self, corner_radius=16)
        left_panel.grid(row=1, column=0, padx=(20, 10), pady=(10, 20), sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_panel, text="URL", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 8), sticky="w"
        )
        self.url_entry = ctk.CTkEntry(
            left_panel,
            textvariable=self.url_var,
            placeholder_text="Cole o link do YouTube, Instagram ou Twitter/X",
            height=42,
        )
        self.url_entry.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="ew")
        self.url_entry.bind("<Return>", lambda _event: self._analyze_url())

        actions = ctk.CTkFrame(left_panel, fg_color="transparent")
        actions.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)
        ctk.CTkButton(actions, text="Colar", command=self._paste_from_clipboard).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.analyze_button = ctk.CTkButton(actions, text="Analisar", command=self._analyze_url)
        self.analyze_button.grid(row=0, column=1, padx=8, sticky="ew")
        ctk.CTkButton(actions, text="Adicionar à fila", command=self._enqueue_download).grid(row=0, column=2, padx=(8, 0), sticky="ew")

        ctk.CTkLabel(left_panel, text="Formato", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=3, column=0, padx=20, pady=(0, 8), sticky="w"
        )
        ctk.CTkSegmentedButton(
            left_panel,
            values=["video", "audio"],
            variable=self.format_var,
            dynamic_resizing=False,
        ).grid(row=4, column=0, padx=20, pady=(0, 16), sticky="ew")

        note = ctk.CTkLabel(
            left_panel,
            text=(
                "Vídeo usa a melhor qualidade disponível. "
                + (
                    "Como o ffmpeg está instalado, o app pode combinar vídeo e áudio de qualidade alta."
                    if has_ffmpeg()
                    else "Instale o ffmpeg para liberar combinações de vídeo+áudio em qualidade ainda maior no YouTube."
                )
            ),
            justify="left",
            wraplength=420,
            text_color=("gray35", "gray70"),
        )
        note.grid(row=5, column=0, padx=20, pady=(0, 16), sticky="w")

        preview_frame = ctk.CTkFrame(left_panel, corner_radius=14)
        preview_frame.grid(row=6, column=0, padx=20, pady=(0, 16), sticky="ew")
        preview_frame.grid_columnconfigure(1, weight=1)

        self.thumbnail_label = ctk.CTkLabel(preview_frame, text="Sem preview", width=180, height=120)
        self.thumbnail_label.grid(row=0, column=0, rowspan=4, padx=16, pady=16)
        ctk.CTkLabel(preview_frame, textvariable=self.preview_title_var, font=ctk.CTkFont(size=18, weight="bold"), wraplength=300, justify="left").grid(
            row=0, column=1, padx=(0, 16), pady=(16, 6), sticky="w"
        )
        ctk.CTkLabel(preview_frame, textvariable=self.preview_author_var, wraplength=300, justify="left").grid(
            row=1, column=1, padx=(0, 16), pady=6, sticky="w"
        )
        ctk.CTkLabel(preview_frame, textvariable=self.preview_meta_var, wraplength=300, justify="left").grid(
            row=2, column=1, padx=(0, 16), pady=6, sticky="w"
        )
        ctk.CTkLabel(preview_frame, textvariable=self.preview_source_var, wraplength=300, justify="left").grid(
            row=3, column=1, padx=(0, 16), pady=(6, 16), sticky="w"
        )

        status_frame = ctk.CTkFrame(left_panel, corner_radius=14)
        status_frame.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(status_frame, text="Status Atual", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )
        ctk.CTkLabel(status_frame, textvariable=self.current_job_var, wraplength=420, justify="left").grid(
            row=1, column=0, padx=16, pady=(0, 6), sticky="w"
        )
        ctk.CTkLabel(status_frame, textvariable=self.current_message_var, wraplength=420, justify="left").grid(
            row=2, column=0, padx=16, pady=(0, 10), sticky="w"
        )
        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)
        ctk.CTkLabel(status_frame, textvariable=self.feedback_var, wraplength=420, justify="left", text_color=("gray35", "gray70")).grid(
            row=4, column=0, padx=16, pady=(0, 16), sticky="w"
        )

        right_panel = ctk.CTkFrame(self, corner_radius=16)
        right_panel.grid(row=1, column=1, padx=(10, 20), pady=(10, 20), sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_panel, text="Fila de downloads", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 6), sticky="w"
        )
        ctk.CTkLabel(right_panel, textvariable=self.stats_var, text_color=("gray35", "gray70")).grid(
            row=0, column=0, padx=20, pady=(24, 6), sticky="e"
        )

        self.queue_scroll = ctk.CTkScrollableFrame(right_panel, corner_radius=14)
        self.queue_scroll.grid(row=1, column=0, padx=20, pady=(8, 20), sticky="nsew")
        self.queue_scroll.grid_columnconfigure(0, weight=1)

    def _push_latest(self, event_queue: queue.Queue[dict[str, Any]], payload: dict[str, Any]) -> None:
        while True:
            try:
                event_queue.get_nowait()
            except queue.Empty:
                break
        try:
            event_queue.put_nowait(payload)
        except queue.Full:
            pass

    def _push_queue_state(self, payload: dict[str, Any]) -> None:
        self._push_latest(self.queue_events, payload)

    def _push_preview_state(self, payload: dict[str, Any]) -> None:
        self._push_latest(self.preview_events, payload)

    def _paste_from_clipboard(self) -> None:
        try:
            self.url_var.set(self.clipboard_get().strip())
        except Exception:
            messagebox.showerror("Clipboard", "Não foi possível ler a área de transferência.")

    def _analyze_url(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("URL obrigatória", "Cole uma URL antes de analisar.")
            return

        self.preview_request_id += 1
        request_id = self.preview_request_id
        self.feedback_var.set("Analisando mídia...")
        self.analyze_button.configure(state="disabled")

        threading.Thread(target=self._preview_worker, args=(request_id, url), daemon=True).start()

    def _preview_worker(self, request_id: int, url: str) -> None:
        try:
            info = get_media_info_data(url)
            image_bytes = None
            thumbnail_url = info.get("thumbnail")
            if thumbnail_url:
                response = requests.get(thumbnail_url, timeout=15)
                response.raise_for_status()
                image_bytes = response.content
            self._push_preview_state({"request_id": request_id, "info": info, "image_bytes": image_bytes})
        except Exception as exc:
            self._push_preview_state({"request_id": request_id, "error": str(exc)})

    def _enqueue_download(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("URL obrigatória", "Cole uma URL antes de adicionar à fila.")
            return

        try:
            self.queue_manager.enqueue(url, self.format_var.get())
            self.feedback_var.set("Download adicionado à fila.")
        except Exception as exc:
            messagebox.showerror("Erro ao adicionar", str(exc))

    def _open_downloads_folder(self) -> None:
        try:
            open_path(self.paths.downloads_dir)
        except Exception as exc:
            messagebox.showerror("Erro ao abrir pasta", str(exc))

    def _open_job_file(self, filepath: str) -> None:
        try:
            open_path(filepath)
        except Exception as exc:
            messagebox.showerror("Erro ao abrir arquivo", str(exc))

    def _cancel_job(self, job_id: str) -> None:
        ok, message = self.queue_manager.cancel(job_id)
        if not ok:
            messagebox.showwarning("Cancelar download", message)

    def _retry_job(self, job_id: str) -> None:
        _job, error = self.queue_manager.retry(job_id)
        if error:
            messagebox.showwarning("Reenfileirar download", error)

    def _process_ui_events(self) -> None:
        latest_queue_payload = None
        latest_preview_payload = None

        while True:
            try:
                latest_queue_payload = self.queue_events.get_nowait()
            except queue.Empty:
                break

        while True:
            try:
                latest_preview_payload = self.preview_events.get_nowait()
            except queue.Empty:
                break

        if latest_queue_payload is not None:
            self._render_queue_state(latest_queue_payload)
        if latest_preview_payload is not None:
            self._render_preview_state(latest_preview_payload)

        self.after(150, self._process_ui_events)

    def _render_preview_state(self, payload: dict[str, Any]) -> None:
        if payload["request_id"] != self.preview_request_id:
            return

        self.analyze_button.configure(state="normal")

        if payload.get("error"):
            self.feedback_var.set(f"Erro ao analisar: {payload['error']}")
            messagebox.showerror("Erro ao analisar mídia", payload["error"])
            return

        info = payload["info"]
        self.preview_title_var.set(info.get("title") or "Sem título")
        self.preview_author_var.set(f"Autor: {info.get('author') or 'Desconhecido'}")
        self.preview_meta_var.set(
            f"Duração: {format_duration(info.get('length'))}  •  Views: {format_views(info.get('views'))}"
        )
        self.preview_source_var.set(f"Origem: {str(info.get('source', '-')).title()}")
        self.feedback_var.set("Preview carregado com sucesso.")

        image_bytes = payload.get("image_bytes")
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            image.thumbnail((220, 140))
            self.thumbnail_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
            self.thumbnail_label.configure(text="", image=self.thumbnail_image)
        else:
            self.thumbnail_image = None
            self.thumbnail_label.configure(text="Sem thumbnail", image=None)

    def _render_queue_state(self, payload: dict[str, Any]) -> None:
        jobs = payload["jobs"]
        stats = payload["stats"]
        self.stats_var.set(
            f"{stats['total']} itens  •  {stats['queued']} na fila  •  {stats['completed']} concluídos  •  {stats['failed']} falhas"
        )

        current_job = None
        for job in jobs:
            if job["id"] == stats["current_job_id"]:
                current_job = job
                break

        if current_job:
            title = current_job.get("title") or current_job.get("filename") or current_job["url"]
            self.current_job_var.set(f"Em andamento: {title}")
            self.current_message_var.set(current_job.get("message") or "Processando...")
            self.progress_bar.set(max(0, min(1, float(current_job.get("percent", 0)) / 100)))
        else:
            self.current_job_var.set("Fila ociosa")
            self.current_message_var.set("Nenhum download em andamento.")
            self.progress_bar.set(0)

        for widget in self.queue_scroll.winfo_children():
            widget.destroy()

        if not jobs:
            ctk.CTkLabel(self.queue_scroll, text="Nenhum download ainda.", text_color=("gray35", "gray70")).grid(
                row=0, column=0, padx=12, pady=12, sticky="w"
            )
            return

        for row_index, job in enumerate(jobs):
            card = ctk.CTkFrame(self.queue_scroll, corner_radius=12)
            card.grid(row=row_index, column=0, padx=8, pady=8, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            title = job.get("title") or job.get("filename") or job["url"]
            status_line = f"{job['status'].upper()}  •  {job.get('percent', 0):.1f}%  •  {job['format']}"
            if job.get("queue_position"):
                status_line += f"  •  posição {job['queue_position']}"

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=16, weight="bold"), wraplength=420, justify="left").grid(
                row=0, column=0, padx=14, pady=(14, 6), sticky="w"
            )
            ctk.CTkLabel(card, text=status_line, text_color=("gray35", "gray70")).grid(
                row=1, column=0, padx=14, pady=2, sticky="w"
            )
            ctk.CTkLabel(card, text=job.get("message") or "-", wraplength=420, justify="left").grid(
                row=2, column=0, padx=14, pady=2, sticky="w"
            )
            progress = ctk.CTkProgressBar(card)
            progress.grid(row=3, column=0, padx=14, pady=(8, 12), sticky="ew")
            progress.set(max(0, min(1, float(job.get("percent", 0)) / 100)))

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.grid(row=4, column=0, padx=14, pady=(0, 14), sticky="w")

            if job["can_cancel"]:
                ctk.CTkButton(actions, text="Cancelar", width=110, command=lambda job_id=job["id"]: self._cancel_job(job_id)).pack(
                    side="left", padx=(0, 8)
                )
            if job["can_retry"]:
                ctk.CTkButton(actions, text="Tentar novamente", width=140, command=lambda job_id=job["id"]: self._retry_job(job_id)).pack(
                    side="left", padx=(0, 8)
                )
            if job["status"] == "completed" and job.get("filepath"):
                ctk.CTkButton(
                    actions,
                    text="Abrir arquivo",
                    width=120,
                    command=lambda filepath=job["filepath"]: self._open_job_file(filepath),
                ).pack(side="left")

    def on_close(self) -> None:
        self.queue_manager.stop()
        self.destroy()


def main() -> None:
    app = PlaydownApp(create_app_paths())
    app.mainloop()
