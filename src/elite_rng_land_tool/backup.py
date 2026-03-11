from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .parser import iter_log_files
from .utils import ensure_directory, safe_relative_path


class BackupSyncError(Exception):
    pass


@dataclass(slots=True)
class BackupSyncResult:
    source_dir: Path
    backup_dir: Path
    scanned_files: int
    copied_files: int
    skipped_files: int
    errors: list[str] = field(default_factory=list)


def _should_copy_file(source_path: Path, backup_path: Path) -> bool:
    if not backup_path.exists():
        return True

    try:
        source_stat = source_path.stat()
        backup_stat = backup_path.stat()
    except OSError:
        return True

    if source_stat.st_size != backup_stat.st_size:
        return True

    return source_stat.st_mtime_ns > backup_stat.st_mtime_ns


def sync_log_backup(source_dir: Path, backup_dir: Path) -> BackupSyncResult:
    source_dir = source_dir.expanduser().resolve()
    backup_dir = ensure_directory(backup_dir.expanduser().resolve())

    if not source_dir.exists() or not source_dir.is_dir():
        raise BackupSyncError(f"VRChat ログフォルダが見つかりません: {source_dir}")

    log_files = iter_log_files(source_dir)
    copied_files = 0
    skipped_files = 0
    errors: list[str] = []

    for source_path in log_files:
        relative_path = Path(safe_relative_path(source_path, source_dir))
        backup_path = backup_dir / relative_path

        try:
            if not _should_copy_file(source_path, backup_path):
                continue

            ensure_directory(backup_path.parent)
            shutil.copy2(source_path, backup_path)
            copied_files += 1
        except OSError as exc:
            skipped_files += 1
            errors.append(f"{source_path}: {exc}")

    return BackupSyncResult(
        source_dir=source_dir,
        backup_dir=backup_dir,
        scanned_files=len(log_files),
        copied_files=copied_files,
        skipped_files=skipped_files,
        errors=errors,
    )
