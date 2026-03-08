from __future__ import annotations

from collections import Counter

from .exporter import prepare_output_dir, write_all_outputs
from .models import AggregateOptions, AggregateResult, CsvOutputPaths, FileAuraRow, SummaryRow
from .parser import iter_log_files, parse_log_file
from .utils import safe_relative_path


class AggregationError(Exception):
    pass


def build_summary_rows(aura_counts: Counter[str]) -> list[SummaryRow]:
    total = sum(aura_counts.values())
    return [
        SummaryRow(
            aura=aura,
            count=count,
            percentage=(count / total * 100.0) if total else 0.0,
        )
        for aura, count in sorted(aura_counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]


def run_aggregation(options: AggregateOptions) -> AggregateResult:
    input_dir = options.input_dir.expanduser().resolve()
    output_root = options.output_root.expanduser().resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        raise AggregationError("集計元フォルダが見つかりません。")

    log_files = iter_log_files(input_dir)
    if not log_files:
        raise AggregationError("指定フォルダ配下に .txt / .log ファイルが見つかりません。")

    aura_counts: Counter[str] = Counter()
    by_file_rows: list[FileAuraRow] = []
    errors: list[str] = []
    matched_files = 0
    skipped_files = 0

    for file_path in log_files:
        parsed = parse_log_file(file_path, dedupe_lines=options.dedupe_lines)

        if parsed.error:
            skipped_files += 1
            errors.append(f"{file_path}: {parsed.error}")
            continue

        if parsed.warning:
            errors.append(f"{file_path}: {parsed.warning}")

        if parsed.matched_count > 0:
            matched_files += 1

        aura_counts.update(parsed.aura_counts)

        for aura, count in sorted(parsed.aura_counts.items(), key=lambda item: (-item[1], item[0].lower())):
            by_file_rows.append(
                FileAuraRow(
                    file=safe_relative_path(parsed.path, input_dir),
                    aura=aura,
                    count=count,
                )
            )

    summary_rows = build_summary_rows(aura_counts)
    by_file_rows.sort(key=lambda row: (row.file.lower(), -row.count, row.aura.lower()))

    output_dir = prepare_output_dir(output_root)
    csv_paths = CsvOutputPaths(
        summary=output_dir / "aura_summary.csv",
        detailed=output_dir / "aura_summary_detailed.csv",
        by_file=output_dir / "aura_summary_by_file.csv",
        error_log=(output_dir / "aura_errors.log") if errors else None,
    )

    result = AggregateResult(
        input_dir=input_dir,
        output_dir=output_dir,
        scanned_files=len(log_files),
        matched_files=matched_files,
        skipped_files=skipped_files,
        total_detections=sum(aura_counts.values()),
        summary_rows=summary_rows,
        by_file_rows=by_file_rows,
        errors=errors,
        csv_paths=csv_paths,
    )
    write_all_outputs(result)
    return result
