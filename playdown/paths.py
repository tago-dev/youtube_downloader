from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "Playdown"
APP_AUTHOR = "Tiago"


def _default_downloads_root() -> Path:
    try:
        from platformdirs import user_downloads_path

        return Path(user_downloads_path())
    except Exception:
        return Path.home() / "Downloads"


@dataclass(frozen=True)
class AppPaths:
    data_dir: Path
    downloads_dir: Path
    queue_state_file: Path

    def ensure(self) -> "AppPaths":
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.queue_state_file.parent.mkdir(parents=True, exist_ok=True)
        return self


def create_app_paths() -> AppPaths:
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    downloads_dir = _default_downloads_root() / APP_NAME
    queue_state_file = data_dir / "queue_state.json"
    return AppPaths(
        data_dir=data_dir,
        downloads_dir=downloads_dir,
        queue_state_file=queue_state_file,
    ).ensure()
