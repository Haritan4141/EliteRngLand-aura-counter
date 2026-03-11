from __future__ import annotations

import codecs
import os
import re
from collections import Counter
from pathlib import Path

from .models import ParsedLogFile
from .utils import VRCHAT_BACKUP_DIR_NAME


LOG_SUFFIXES = {".txt", ".log"}
EXCLUDED_DIRECTORY_PREFIXES = ("aura_results_",)
EXCLUDED_DIRECTORY_NAMES = {".venv", "build", "dist", "__pycache__", VRCHAT_BACKUP_DIR_NAME}
AURA_PATTERN = re.compile(r"Firing (?P<aura>.+)'s(?: unique)? cutscene\.\.\.")


def iter_log_files(root_dir: Path) -> list[Path]:
    results: list[Path] = []
    for current_root, directory_names, file_names in os.walk(root_dir):
        directory_names[:] = [
            name
            for name in directory_names
            if name not in EXCLUDED_DIRECTORY_NAMES and not name.startswith(EXCLUDED_DIRECTORY_PREFIXES)
        ]
        for file_name in sorted(file_names):
            if Path(file_name).suffix.lower() in LOG_SUFFIXES:
                results.append(Path(current_root) / file_name)
    return sorted(results)


def _looks_like_utf16(sample: bytes) -> bool:
    if sample.startswith((codecs.BOM_UTF16_BE, codecs.BOM_UTF16_LE)):
        return True
    if not sample:
        return False
    return sample.count(b"\x00") / len(sample) > 0.2


def detect_encoding(file_path: Path) -> str:
    with file_path.open("rb") as handle:
        sample = handle.read(4096)

    if sample.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if _looks_like_utf16(sample):
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                sample.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue

    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue

    return "latin-1"


def parse_log_file(file_path: Path, *, dedupe_lines: bool = False) -> ParsedLogFile:
    try:
        encoding = detect_encoding(file_path)
    except OSError as exc:
        return ParsedLogFile(path=file_path, encoding="unknown", error=str(exc))

    counts: Counter[str] = Counter()
    seen_matches: set[str] | None = set() if dedupe_lines else None

    try:
        with file_path.open("r", encoding=encoding, errors="replace") as handle:
            for raw_line in handle:
                match = AURA_PATTERN.search(raw_line)
                if not match:
                    continue

                aura = match.group("aura").strip()
                if not aura:
                    continue

                if seen_matches is not None:
                    line_key = raw_line.strip()
                    if line_key in seen_matches:
                        continue
                    seen_matches.add(line_key)

                counts[aura] += 1
    except OSError as exc:
        return ParsedLogFile(path=file_path, encoding=encoding, error=str(exc))

    return ParsedLogFile(
        path=file_path,
        encoding=encoding,
        matched_count=sum(counts.values()),
        aura_counts=counts,
    )
