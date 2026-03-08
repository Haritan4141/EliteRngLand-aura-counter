from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_dir / relative_path


def timestamp_label() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def open_path(path: Path) -> None:
    resolved = str(path)
    if sys.platform.startswith("win"):
        os.startfile(resolved)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", resolved])
        return
    subprocess.Popen(["xdg-open", resolved])
