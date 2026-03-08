from __future__ import annotations

import csv
from pathlib import Path

from .models import AggregateResult, FileAuraRow, SummaryRow
from .utils import ensure_directory, timestamp_label


def prepare_output_dir(output_root: Path) -> Path:
    target_dir = ensure_directory(output_root) / f"aura_results_{timestamp_label()}"
    return ensure_directory(target_dir)


def write_summary_csv(file_path: Path, rows: list[SummaryRow]) -> None:
    with file_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Aura", "Count"])
        for row in rows:
            writer.writerow([row.aura, row.count])


def write_detailed_csv(file_path: Path, rows: list[SummaryRow]) -> None:
    with file_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Aura", "Count", "Percentage"])
        for row in rows:
            writer.writerow([row.aura, row.count, f"{row.percentage:.2f}"])


def write_by_file_csv(file_path: Path, rows: list[FileAuraRow]) -> None:
    with file_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["File", "Aura", "Count"])
        for row in rows:
            writer.writerow([row.file, row.aura, row.count])


def write_error_log(file_path: Path, errors: list[str]) -> None:
    file_path.write_text("\n".join(errors) + ("\n" if errors else ""), encoding="utf-8")


def write_all_outputs(result: AggregateResult) -> None:
    write_summary_csv(result.csv_paths.summary, result.summary_rows)
    write_detailed_csv(result.csv_paths.detailed, result.summary_rows)
    write_by_file_csv(result.csv_paths.by_file, result.by_file_rows)
    if result.errors and result.csv_paths.error_log is not None:
        write_error_log(result.csv_paths.error_log, result.errors)
