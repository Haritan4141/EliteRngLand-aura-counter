from __future__ import annotations

import argparse
from pathlib import Path

from .gui import launch_gui
from .models import AggregateOptions
from .service import AggregationError, run_aggregation
from .utils import open_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Elite's RNG Land のログから aura 出現数を集計します。",
    )
    parser.add_argument("--input-dir", type=Path, help="集計元フォルダ")
    parser.add_argument("--output-dir", type=Path, help="CSV 保存先フォルダ")
    parser.add_argument("--dedupe", action="store_true", help="完全一致の重複行を除外")
    parser.add_argument("--no-open", action="store_true", help="集計後に CSV を開かない")
    return parser


def run_cli(input_dir: Path, output_dir: Path | None, dedupe: bool, no_open: bool) -> int:
    target_output = output_dir or input_dir

    try:
        result = run_aggregation(
            AggregateOptions(
                input_dir=input_dir,
                output_root=target_output,
                dedupe_lines=dedupe,
                auto_open_summary=not no_open,
            )
        )
    except AggregationError as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"Scanned files   : {result.scanned_files}")
    print(f"Matched files   : {result.matched_files}")
    print(f"Total detections: {result.total_detections}")
    print(f"Output folder   : {result.output_dir}")

    for row in result.summary_rows[:20]:
        print(f"{row.aura:20} {row.count:>6} ({row.percentage:>6.2f}%)")

    if not no_open:
        try:
            open_path(result.csv_paths.summary)
        except OSError:
            pass

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input_dir:
        return run_cli(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            dedupe=args.dedupe,
            no_open=args.no_open,
        )

    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
