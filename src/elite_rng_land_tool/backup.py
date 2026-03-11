from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .parser import detect_encoding, extract_aura_name, iter_log_files
from .utils import (
    AURA_ONLY_DIR_NAME,
    UNKNOWN_PATTERNS_DIR_NAME,
    UNKNOWN_PATTERNS_LOG_NAME,
    ensure_directory,
    safe_relative_path,
)


class BackupSyncError(Exception):
    pass


@dataclass(slots=True)
class BackupSyncResult:
    source_dir: Path
    backup_dir: Path
    aura_only_dir: Path
    unknown_patterns_log: Path
    scanned_files: int
    copied_files: int
    aura_only_updated_files: int
    aura_only_removed_files: int
    unknown_updated_files: int
    unknown_removed_files: int
    unknown_pattern_lines: int
    skipped_files: int
    errors: list[str] = field(default_factory=list)


def _should_copy_file(source_path: Path, target_path: Path) -> bool:
    if not target_path.exists():
        return True

    try:
        source_stat = source_path.stat()
        target_stat = target_path.stat()
    except OSError:
        return True

    if source_stat.st_size != target_stat.st_size:
        return True

    return source_stat.st_mtime_ns > target_stat.st_mtime_ns


def _should_refresh_filtered_file(source_path: Path, filtered_path: Path) -> bool:
    if not filtered_path.exists():
        return True

    try:
        source_stat = source_path.stat()
        filtered_stat = filtered_path.stat()
    except OSError:
        return True

    return source_stat.st_mtime_ns > filtered_stat.st_mtime_ns


def _scan_source_file(source_path: Path) -> tuple[list[str], list[str]]:
    encoding = detect_encoding(source_path)
    aura_lines: list[str] = []
    unknown_lines: list[str] = []

    with source_path.open("r", encoding=encoding, errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if extract_aura_name(raw_line):
                aura_lines.append(raw_line)
                continue

            lowered = raw_line.lower()
            if "elite's rng land" in lowered or "cutscene" in lowered:
                unknown_lines.append(f"{line_number}\t{raw_line.rstrip()}\n")

    return aura_lines, unknown_lines


def _write_filtered_file(lines: list[str], target_path: Path) -> tuple[bool, bool]:
    if not lines:
        if target_path.exists():
            target_path.unlink()
            return False, True
        return False, False

    ensure_directory(target_path.parent)
    target_path.write_text("".join(lines), encoding="utf-8")
    return True, False


def _rebuild_unknown_patterns_log(
    unknown_snapshot_dir: Path,
    unknown_patterns_log: Path,
) -> int:
    snapshot_files = sorted(path for path in unknown_snapshot_dir.rglob("*") if path.is_file())
    if not snapshot_files:
        if unknown_patterns_log.exists():
            unknown_patterns_log.unlink()
        return 0

    lines: list[str] = []
    total_unknown_lines = 0

    for snapshot_path in snapshot_files:
        relative_path = snapshot_path.relative_to(unknown_snapshot_dir)
        content_lines = snapshot_path.read_text(encoding="utf-8").splitlines()
        if not content_lines:
            continue

        lines.append(f"[{relative_path.as_posix()}]\n")
        for entry in content_lines:
            lines.append(f"{entry}\n")
            total_unknown_lines += 1
        lines.append("\n")

    ensure_directory(unknown_patterns_log.parent)
    unknown_patterns_log.write_text("".join(lines), encoding="utf-8")
    return total_unknown_lines


def sync_log_backup(source_dir: Path, backup_dir: Path) -> BackupSyncResult:
    source_dir = source_dir.expanduser().resolve()
    backup_dir = ensure_directory(backup_dir.expanduser().resolve())
    aura_only_dir = ensure_directory(backup_dir / AURA_ONLY_DIR_NAME)
    unknown_snapshot_dir = ensure_directory(backup_dir / UNKNOWN_PATTERNS_DIR_NAME)
    unknown_patterns_log = backup_dir / UNKNOWN_PATTERNS_LOG_NAME

    if not source_dir.exists() or not source_dir.is_dir():
        raise BackupSyncError(f"VRChat ログフォルダが見つかりません: {source_dir}")

    log_files = iter_log_files(source_dir)
    copied_files = 0
    aura_only_updated_files = 0
    aura_only_removed_files = 0
    unknown_updated_files = 0
    unknown_removed_files = 0
    unknown_needs_rebuild = not unknown_patterns_log.exists()
    skipped_files = 0
    errors: list[str] = []

    for source_path in log_files:
        relative_path = Path(safe_relative_path(source_path, source_dir))
        backup_path = backup_dir / relative_path
        aura_only_path = aura_only_dir / relative_path
        unknown_snapshot_path = unknown_snapshot_dir / relative_path

        try:
            if _should_copy_file(source_path, backup_path):
                ensure_directory(backup_path.parent)
                shutil.copy2(source_path, backup_path)
                copied_files += 1

            if _should_refresh_filtered_file(source_path, aura_only_path) or _should_refresh_filtered_file(
                source_path, unknown_snapshot_path
            ):
                aura_lines, unknown_lines = _scan_source_file(source_path)

                aura_updated, aura_removed = _write_filtered_file(aura_lines, aura_only_path)
                if aura_updated:
                    aura_only_updated_files += 1
                if aura_removed:
                    aura_only_removed_files += 1

                unknown_updated, unknown_removed = _write_filtered_file(unknown_lines, unknown_snapshot_path)
                if unknown_updated:
                    unknown_updated_files += 1
                if unknown_removed:
                    unknown_removed_files += 1

                unknown_needs_rebuild = True
        except OSError as exc:
            skipped_files += 1
            errors.append(f"{source_path}: {exc}")

    unknown_pattern_lines = _rebuild_unknown_patterns_log(unknown_snapshot_dir, unknown_patterns_log) if unknown_needs_rebuild else 0
    if not unknown_needs_rebuild and unknown_patterns_log.exists():
        unknown_pattern_lines = sum(
            1
            for line in unknown_patterns_log.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("[")
        )

    return BackupSyncResult(
        source_dir=source_dir,
        backup_dir=backup_dir,
        aura_only_dir=aura_only_dir,
        unknown_patterns_log=unknown_patterns_log,
        scanned_files=len(log_files),
        copied_files=copied_files,
        aura_only_updated_files=aura_only_updated_files,
        aura_only_removed_files=aura_only_removed_files,
        unknown_updated_files=unknown_updated_files,
        unknown_removed_files=unknown_removed_files,
        unknown_pattern_lines=unknown_pattern_lines,
        skipped_files=skipped_files,
        errors=errors,
    )
