from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .utils import ensure_directory


APP_SETTINGS_DIR_NAME = "EliteRngLandAuraTool"
SETTINGS_FILE_NAME = "settings.json"


@dataclass(slots=True)
class UserSettings:
    last_input_dir: str = ""
    last_output_dir: str = ""
    dedupe_lines: bool = False


def get_settings_path() -> Path:
    base_dir = Path(os.getenv("APPDATA", Path.home() / ".config"))
    return ensure_directory(base_dir / APP_SETTINGS_DIR_NAME) / SETTINGS_FILE_NAME


def load_settings() -> UserSettings:
    settings_path = get_settings_path()
    if not settings_path.exists():
        return UserSettings()

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return UserSettings()

    return UserSettings(
        last_input_dir=str(data.get("last_input_dir", "")),
        last_output_dir=str(data.get("last_output_dir", "")),
        dedupe_lines=bool(data.get("dedupe_lines", False)),
    )


def save_settings(settings: UserSettings) -> None:
    settings_path = get_settings_path()
    try:
        settings_path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return
