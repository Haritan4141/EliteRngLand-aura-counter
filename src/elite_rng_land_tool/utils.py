from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


VRCHAT_BACKUP_DIR_NAME = "VRChatLogsBackup"
AURA_ONLY_DIR_NAME = "aura_only"
UNKNOWN_PATTERNS_DIR_NAME = "_unknown_patterns"
UNKNOWN_PATTERNS_LOG_NAME = "unknown_aura_patterns.log"


def resource_path(relative_path: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_dir / relative_path


def timestamp_label() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_user_profile_dir() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home())))


def get_default_vrchat_log_dir() -> Path:
    return get_user_profile_dir() / "AppData" / "LocalLow" / "VRChat" / "VRChat"


def get_default_output_dir() -> Path:
    return get_user_profile_dir() / "Documents" / "Elite's RNG Land" / "exports"


def get_default_backup_dir() -> Path:
    return get_default_vrchat_log_dir() / VRCHAT_BACKUP_DIR_NAME


def get_default_aura_backup_dir() -> Path:
    return get_default_backup_dir() / AURA_ONLY_DIR_NAME


def get_default_unknown_patterns_log_path() -> Path:
    return get_default_backup_dir() / UNKNOWN_PATTERNS_LOG_NAME


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
