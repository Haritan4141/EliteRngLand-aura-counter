from __future__ import annotations

import csv
from pathlib import Path

from .utils import resource_path


def format_odds(odds_value: int | None) -> str:
    if odds_value is None:
        return "-"
    return f"1 / {odds_value:,}"


def get_default_odds_file() -> Path:
    return resource_path("aura_odds.csv")


def load_aura_odds(file_path: Path | None = None) -> dict[str, int]:
    target_path = file_path or get_default_odds_file()
    if not target_path.exists():
        return {}

    odds_by_aura: dict[str, int] = {}

    try:
        with target_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 2:
                    continue

                aura = row[0].strip()
                odds_text = row[1].strip().replace(",", "")
                if not aura or not odds_text:
                    continue

                try:
                    odds_by_aura[aura] = int(odds_text)
                except ValueError:
                    continue
    except OSError:
        return {}

    return odds_by_aura
