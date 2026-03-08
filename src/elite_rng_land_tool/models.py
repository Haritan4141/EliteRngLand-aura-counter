from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ParsedLogFile:
    path: Path
    encoding: str
    matched_count: int = 0
    aura_counts: Counter[str] = field(default_factory=Counter)
    warning: str | None = None
    error: str | None = None


@dataclass(slots=True)
class SummaryRow:
    aura: str
    count: int
    percentage: float
    odds_value: int | None = None
    odds_display: str = "-"


@dataclass(slots=True)
class FileAuraRow:
    file: str
    aura: str
    count: int
    odds_value: int | None = None
    odds_display: str = "-"


@dataclass(slots=True)
class CsvOutputPaths:
    summary: Path
    detailed: Path
    by_file: Path
    error_log: Path | None = None


@dataclass(slots=True)
class AggregateOptions:
    input_dir: Path
    output_root: Path
    dedupe_lines: bool = False
    auto_open_summary: bool = True


@dataclass(slots=True)
class AggregateResult:
    input_dir: Path
    output_dir: Path
    scanned_files: int
    matched_files: int
    skipped_files: int
    total_detections: int
    summary_rows: list[SummaryRow]
    by_file_rows: list[FileAuraRow]
    errors: list[str]
    csv_paths: CsvOutputPaths
