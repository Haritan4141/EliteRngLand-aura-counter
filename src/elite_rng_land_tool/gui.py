from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .backup import BackupSyncError, BackupSyncResult, sync_log_backup
from .models import AggregateOptions, AggregateResult, SummaryRow
from .service import AggregationError, run_aggregation
from .settings import UserSettings, load_settings, save_settings
from .utils import (
    ensure_directory,
    get_default_aura_backup_dir,
    get_default_backup_dir,
    get_default_output_dir,
    get_default_vrchat_log_dir,
    open_path,
    resource_path,
)
from .version import APP_NAME, APP_VERSION

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_ENABLED = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    DND_ENABLED = False


BACKUP_INTERVAL_MS = 5 * 60 * 1000


class AuraCounterGui:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.root = TkinterDnD.Tk() if DND_ENABLED and TkinterDnD is not None else tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1260x820")
        self.root.minsize(1120, 700)

        self.current_result: AggregateResult | None = None
        self.display_rows: list[SummaryRow] = []
        self.sort_column = "odds"
        self.sort_descending = True
        self.aggregation_in_progress = False
        self.backup_in_progress = False
        self.pending_backup_aggregation = False

        default_input = get_default_vrchat_log_dir()
        default_output = get_default_output_dir()
        default_backup = get_default_backup_dir()
        default_aura_backup = get_default_aura_backup_dir()
        try:
            ensure_directory(default_output)
        except OSError:
            pass
        try:
            ensure_directory(default_backup)
        except OSError:
            pass
        try:
            ensure_directory(default_aura_backup)
        except OSError:
            pass

        self.input_dir_var = tk.StringVar(value=str(default_input))
        self.output_dir_var = tk.StringVar(value=str(default_output))
        self.status_var = tk.StringVar(
            value="集計元フォルダと保存先フォルダを自動設定しました。必要なら変更してから集計してください。"
        )
        self.backup_status_var = tk.StringVar(
            value="ログバックアップは起動中に 5 分ごとに同期され、バックアップ集計は aura_only を使用します。"
        )
        self.save_path_var = tk.StringVar(value="-")
        self.file_count_var = tk.StringVar(value="0")
        self.total_count_var = tk.StringVar(value="0")
        self.matched_file_var = tk.StringVar(value="0")
        self.dedupe_var = tk.BooleanVar(value=self.settings.dedupe_lines)

        self._configure_style()
        self._set_window_icon()
        self._build_ui()
        self._bind_events()
        self._start_backup_scheduler()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        bg = "#f3efe6"
        surface = "#fffaf2"
        accent = "#314b63"
        accent_soft = "#d6e4f0"
        text = "#1e2430"

        self.root.configure(bg=bg)

        default_font = ("Yu Gothic UI", 10)
        heading_font = ("Yu Gothic UI Semibold", 10)
        title_font = ("Yu Gothic UI Semibold", 16)

        style.configure(".", background=bg, foreground=text, font=default_font)
        style.configure("Card.TFrame", background=surface, relief="flat")
        style.configure("Header.TLabel", background=bg, foreground=text, font=title_font)
        style.configure("Hint.TLabel", background=bg, foreground="#5e6875")
        style.configure("CardTitle.TLabel", background=surface, foreground=text, font=heading_font)
        style.configure("Value.TLabel", background=surface, foreground=accent, font=("Yu Gothic UI Semibold", 13))
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", padding=(12, 8))
        style.map("Primary.TButton", background=[("active", accent_soft)])
        style.configure("Treeview", rowheight=28, fieldbackground="#ffffff", background="#ffffff")
        style.configure("Treeview.Heading", font=heading_font, background=accent_soft, foreground=text)

    def _set_window_icon(self) -> None:
        icon_path = resource_path("assets/app.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=APP_NAME, style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="VRChat の .txt / .log を再帰検索して aura を集計します。",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        control_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        control_card.grid(row=1, column=0, sticky="ew", pady=(16, 14))
        control_card.columnconfigure(1, weight=1)

        ttk.Label(control_card, text="集計元フォルダ", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(control_card, textvariable=self.input_dir_var).grid(row=0, column=1, sticky="ew", padx=(12, 8))
        ttk.Button(control_card, text="フォルダ選択", command=self.select_input_dir).grid(row=0, column=2, sticky="ew")

        ttk.Label(control_card, text="保存先フォルダ", style="CardTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(control_card, textvariable=self.output_dir_var).grid(row=1, column=1, sticky="ew", padx=(12, 8), pady=(10, 0))
        ttk.Button(control_card, text="保存先選択", command=self.select_output_dir).grid(row=1, column=2, sticky="ew", pady=(10, 0))

        options_row = ttk.Frame(control_card, style="Card.TFrame")
        options_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        options_row.columnconfigure(0, weight=1)
        ttk.Checkbutton(options_row, text="重複行を除外する", variable=self.dedupe_var).grid(row=0, column=0, sticky="w")

        self.auto_run_button = ttk.Button(
            options_row,
            text="自動集計",
            command=self.start_auto_aggregation,
        )
        self.auto_run_button.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self.backup_run_button = ttk.Button(
            options_row,
            text="バックアップ集計",
            command=self.start_backup_aggregation,
        )
        self.backup_run_button.grid(row=0, column=2, sticky="e", padx=(0, 8))

        ttk.Button(
            options_row,
            text="VRChatログを開く",
            command=self.open_default_vrchat_log_dir,
        ).grid(row=0, column=3, sticky="e", padx=(0, 8))

        self.run_button = ttk.Button(
            options_row,
            text="集計開始",
            style="Primary.TButton",
            command=self.start_aggregation,
        )
        self.run_button.grid(row=0, column=4, sticky="e")

        ttk.Label(
            control_card,
            textvariable=self.backup_status_var,
            style="Hint.TLabel",
            wraplength=1120,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        drop_card = ttk.Frame(outer, style="Card.TFrame", padding=14)
        drop_card.grid(row=2, column=0, sticky="ew", pady=(8, 12))
        drop_card.columnconfigure(0, weight=1)

        ttk.Label(drop_card, text="ドラッグ＆ドロップ", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        drop_message = "ここにフォルダをドロップ" if DND_ENABLED else "D&D は tkinterdnd2 導入後に有効になります"
        self.drop_zone = tk.Label(
            drop_card,
            text=drop_message,
            bg="#e8f0f5",
            fg="#314b63",
            relief="ridge",
            bd=2,
            padx=18,
            pady=14,
            font=("Yu Gothic UI Semibold", 11),
        )
        self.drop_zone.grid(row=1, column=0, sticky="ew", pady=(10, 8))

        ttk.Label(drop_card, textvariable=self.status_var, style="Hint.TLabel").grid(row=2, column=0, sticky="w")
        self.progress = ttk.Progressbar(drop_card, mode="indeterminate")
        self.progress.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        content = ttk.Frame(outer)
        content.grid(row=3, column=0, sticky="nsew")
        content.columnconfigure(0, weight=4)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        table_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)

        ttk.Label(table_card, text="集計結果", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")

        self.tree = ttk.Treeview(table_card, columns=("aura", "odds", "count", "percentage"), show="headings")
        self.tree.heading("aura", text="Aura名", command=lambda: self.sort_results("aura"))
        self.tree.heading("odds", text="確率(1/N)", command=lambda: self.sort_results("odds"))
        self.tree.heading("count", text="件数", command=lambda: self.sort_results("count"))
        self.tree.heading("percentage", text="割合(%)", command=lambda: self.sort_results("percentage"))
        self.tree.column("aura", width=180, anchor="w")
        self.tree.column("odds", width=150, anchor="e")
        self.tree.column("count", width=90, anchor="e")
        self.tree.column("percentage", width=110, anchor="e")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)

        action_row = ttk.Frame(table_card, style="Card.TFrame")
        action_row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for index in range(4):
            action_row.columnconfigure(index, weight=1)

        ttk.Button(action_row, text="CSVを開く", command=lambda: self.open_csv("summary")).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(action_row, text="詳細CSV", command=lambda: self.open_csv("detailed")).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(action_row, text="ファイル別CSV", command=lambda: self.open_csv("by_file")).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(action_row, text="結果をコピー", command=self.copy_results).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        side_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        side_card.grid(row=0, column=1, sticky="nsew")
        side_card.columnconfigure(0, weight=1)

        ttk.Label(side_card, text="サマリー", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")

        metrics_row = ttk.Frame(side_card, style="Card.TFrame")
        metrics_row.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for index in range(3):
            metrics_row.columnconfigure(index, weight=1)

        metric_specs = [
            ("対象ログファイル数", self.file_count_var),
            ("Aura検出ありログファイル数", self.matched_file_var),
            ("総検出件数", self.total_count_var),
        ]

        for column_index, (label_text, variable) in enumerate(metric_specs):
            metric_card = ttk.Frame(metrics_row, style="Card.TFrame", padding=(0, 0, 8 if column_index < 2 else 0, 0))
            metric_card.grid(row=0, column=column_index, sticky="ew")
            ttk.Label(metric_card, text=label_text, style="Hint.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(metric_card, textvariable=variable, style="Value.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

        ttk.Label(side_card, text="保存先", style="Hint.TLabel").grid(row=2, column=0, sticky="w", pady=(16, 0))
        ttk.Label(side_card, textvariable=self.save_path_var, style="Value.TLabel", wraplength=560).grid(row=3, column=0, sticky="w")

        ttk.Button(side_card, text="保存先フォルダを開く", command=self.open_output_folder).grid(row=4, column=0, sticky="ew", pady=(10, 0))

        ttk.Label(side_card, text="エラーメッセージ", style="CardTitle.TLabel").grid(row=5, column=0, sticky="w", pady=(12, 0))
        self.error_box = tk.Text(
            side_card,
            height=5,
            wrap="word",
            bg="#fffdf9",
            fg="#3d4653",
            relief="solid",
            bd=1,
            font=("Consolas", 9),
        )
        self.error_box.grid(row=6, column=0, sticky="nsew", pady=(10, 0))
        side_card.rowconfigure(6, weight=1)

    def _bind_events(self) -> None:
        if DND_ENABLED and DND_FILES is not None:
            for widget in (self.root, self.drop_zone):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.on_drop)

    def select_input_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.input_dir_var.get() or str(Path.cwd()))
        if chosen:
            self.input_dir_var.set(chosen)
            if not self.output_dir_var.get().strip():
                self.output_dir_var.set(chosen)

    def select_output_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(Path.cwd()))
        if chosen:
            self.output_dir_var.set(chosen)

    def on_drop(self, event: tk.Event) -> None:
        try:
            raw_paths = self.root.tk.splitlist(event.data)
        except tk.TclError:
            raw_paths = [event.data]

        for raw_path in raw_paths:
            candidate = Path(raw_path)
            if candidate.is_dir():
                self.input_dir_var.set(str(candidate))
                if not self.output_dir_var.get().strip():
                    self.output_dir_var.set(str(candidate))
                self.status_var.set(f"ドラッグ＆ドロップでフォルダを設定しました: {candidate}")
                return

            if candidate.is_file():
                self.input_dir_var.set(str(candidate.parent))
                if not self.output_dir_var.get().strip():
                    self.output_dir_var.set(str(candidate.parent))
                self.status_var.set(f"ファイルの親フォルダを設定しました: {candidate.parent}")
                return

        self.status_var.set("ドロップされたパスを認識できませんでした。")

    def start_aggregation(self) -> None:
        input_dir = Path(self.input_dir_var.get().strip())
        self._start_aggregation_for_dir(input_dir)

    def start_auto_aggregation(self) -> None:
        input_dir = get_default_vrchat_log_dir()
        self.input_dir_var.set(str(input_dir))
        self._start_aggregation_for_dir(input_dir)

    def start_backup_aggregation(self) -> None:
        if self.backup_in_progress:
            messagebox.showinfo("バックアップ実行中", "ログのバックアップ中です。完了してから再度お試しください。")
            return

        input_dir = get_default_aura_backup_dir()
        try:
            ensure_directory(input_dir)
        except OSError as exc:
            messagebox.showerror("入力エラー", f"バックアップフォルダを作成できませんでした。\n{input_dir}\n\n{exc}")
            return

        self.pending_backup_aggregation = True
        self.status_var.set("バックアップを更新してから aura_only を集計します。")
        self._start_backup_sync()

    def open_default_vrchat_log_dir(self) -> None:
        log_dir = get_default_vrchat_log_dir()
        if not log_dir.exists() or not log_dir.is_dir():
            messagebox.showerror("起動エラー", f"VRChat ログフォルダが見つかりません。\n{log_dir}")
            return

        self.input_dir_var.set(str(log_dir))
        self.status_var.set(f"VRChat ログフォルダを開きました: {log_dir}")

        try:
            open_path(log_dir)
        except OSError as exc:
            messagebox.showerror("起動エラー", f"フォルダを開けませんでした: {exc}")

    def _start_backup_scheduler(self) -> None:
        self.root.after(1000, self._run_scheduled_backup)

    def _run_scheduled_backup(self) -> None:
        if not self.aggregation_in_progress and not self.backup_in_progress:
            self._start_backup_sync()
        self.root.after(BACKUP_INTERVAL_MS, self._run_scheduled_backup)

    def _start_backup_sync(self) -> None:
        if self.backup_in_progress:
            return

        source_dir = get_default_vrchat_log_dir()
        backup_dir = get_default_backup_dir()

        self.backup_in_progress = True
        self.backup_status_var.set("ログバックアップを実行中です。")

        worker = threading.Thread(
            target=self._run_backup_worker,
            args=(source_dir, backup_dir),
            daemon=True,
        )
        worker.start()

    def _run_backup_worker(self, source_dir: Path, backup_dir: Path) -> None:
        try:
            result = sync_log_backup(source_dir, backup_dir)
            self.root.after(0, self._on_backup_success, result)
        except BackupSyncError as exc:
            self.root.after(0, self._on_backup_failure, str(exc))
        except Exception as exc:
            self.root.after(0, self._on_backup_failure, f"予期しないエラー: {exc}")

    def _on_backup_success(self, result: BackupSyncResult) -> None:
        self.backup_in_progress = False
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = (
            f"最終バックアップ: {timestamp} / 対象 {result.scanned_files} 件 / "
            f"raw更新 {result.copied_files} 件 / aura_only更新 {result.aura_only_updated_files} 件 / "
            f"未対応候補 {result.unknown_pattern_lines} 行"
        )
        if result.aura_only_removed_files:
            status += f" / aura_only削除 {result.aura_only_removed_files} 件"
        if result.unknown_removed_files:
            status += f" / 未対応候補削除 {result.unknown_removed_files} 件"
        if result.skipped_files:
            status += f" / エラー {result.skipped_files} 件"
        self.backup_status_var.set(status)

        if self.pending_backup_aggregation:
            self.pending_backup_aggregation = False
            self.input_dir_var.set(str(result.aura_only_dir))
            self._start_aggregation_for_dir(result.aura_only_dir)

    def _on_backup_failure(self, message: str) -> None:
        self.backup_in_progress = False
        self.backup_status_var.set(f"ログバックアップエラー: {message}")
        if self.pending_backup_aggregation:
            self.pending_backup_aggregation = False
            messagebox.showerror("バックアップエラー", message)

    def _start_aggregation_for_dir(self, input_dir: Path) -> None:
        output_dir = Path(self.output_dir_var.get().strip() or str(input_dir))

        if not str(input_dir).strip():
            messagebox.showerror("入力エラー", "集計元フォルダを指定してください。")
            return

        if not input_dir.exists() or not input_dir.is_dir():
            messagebox.showerror("入力エラー", f"有効な集計元フォルダを指定してください。\n{input_dir}")
            return

        if not str(output_dir).strip():
            messagebox.showerror("入力エラー", "保存先フォルダを指定してください。")
            return

        try:
            ensure_directory(output_dir)
        except OSError as exc:
            messagebox.showerror("入力エラー", f"保存先フォルダを作成できませんでした。\n{output_dir}\n\n{exc}")
            return

        self._set_busy(True)
        self.status_var.set("集計を実行中です。大量ログでは少し時間がかかります。")
        self.error_box.delete("1.0", "end")

        worker = threading.Thread(
            target=self._run_worker,
            args=(input_dir, output_dir, bool(self.dedupe_var.get())),
            daemon=True,
        )
        worker.start()

    def _run_worker(self, input_dir: Path, output_dir: Path, dedupe_lines: bool) -> None:
        try:
            result = run_aggregation(
                AggregateOptions(
                    input_dir=input_dir,
                    output_root=output_dir,
                    dedupe_lines=dedupe_lines,
                    auto_open_summary=False,
                )
            )
            self.root.after(0, self._on_success, result)
        except AggregationError as exc:
            self.root.after(0, self._on_failure, str(exc))
        except Exception as exc:
            self.root.after(0, self._on_failure, f"予期しないエラー: {exc}")

    def _on_success(self, result: AggregateResult) -> None:
        self._set_busy(False)
        self.current_result = result
        self.display_rows = list(result.summary_rows)
        self.file_count_var.set(str(result.scanned_files))
        self.matched_file_var.set(str(result.matched_files))
        self.total_count_var.set(str(result.total_detections))
        self.save_path_var.set(str(result.output_dir))
        self.status_var.set(
            f"集計完了: {result.total_detections} 件を検出しました。CSV は {result.output_dir} に保存されています。必要なら下の「CSVを開く」を使ってください。"
        )

        self.settings = UserSettings(
            last_input_dir=str(result.input_dir),
            last_output_dir=str(result.output_dir.parent),
            dedupe_lines=bool(self.dedupe_var.get()),
        )
        save_settings(self.settings)

        self.refresh_tree()
        self._render_errors(result.errors)

    def _on_failure(self, message: str) -> None:
        self._set_busy(False)
        self.status_var.set(message)
        messagebox.showerror("集計エラー", message)

    def _set_busy(self, busy: bool) -> None:
        self.aggregation_in_progress = busy
        if busy:
            self.auto_run_button.state(["disabled"])
            self.backup_run_button.state(["disabled"])
            self.run_button.state(["disabled"])
            self.progress.start(10)
        else:
            self.auto_run_button.state(["!disabled"])
            self.backup_run_button.state(["!disabled"])
            self.run_button.state(["!disabled"])
            self.progress.stop()

    def _odds_sort_key(self, row: SummaryRow) -> tuple[bool, int, str]:
        return (row.odds_value is None, row.odds_value or 0, row.aura.lower())

    def refresh_tree(self) -> None:
        rows = list(self.display_rows)

        if self.sort_column == "aura":
            rows.sort(key=lambda row: row.aura.lower(), reverse=self.sort_descending)
        elif self.sort_column == "odds":
            rows.sort(key=self._odds_sort_key)
            if self.sort_descending:
                known_rows = [row for row in rows if row.odds_value is not None]
                unknown_rows = [row for row in rows if row.odds_value is None]
                rows = list(reversed(known_rows)) + unknown_rows
        elif self.sort_column == "percentage":
            if self.sort_descending:
                rows.sort(key=lambda row: (-row.percentage, row.aura.lower()))
            else:
                rows.sort(key=lambda row: (row.percentage, row.aura.lower()))
        else:
            if self.sort_descending:
                rows.sort(key=lambda row: (-row.count, row.aura.lower()))
            else:
                rows.sort(key=lambda row: (row.count, row.aura.lower()))

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for row in rows:
            self.tree.insert("", "end", values=(row.aura, row.odds_display, row.count, f"{row.percentage:.2f}"))

    def sort_results(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = column
            self.sort_descending = column in {"count", "percentage"}
        self.refresh_tree()

    def _render_errors(self, errors: list[str]) -> None:
        self.error_box.delete("1.0", "end")
        if not errors:
            self.error_box.insert("1.0", "エラーはありません。")
            return
        self.error_box.insert("1.0", "\n".join(errors[:100]))

    def open_csv(self, target: str) -> None:
        if not self.current_result:
            messagebox.showinfo("未実行", "先に集計を実行してください。")
            return

        path_map = {
            "summary": self.current_result.csv_paths.summary,
            "detailed": self.current_result.csv_paths.detailed,
            "by_file": self.current_result.csv_paths.by_file,
        }

        try:
            open_path(path_map[target])
        except OSError as exc:
            messagebox.showerror("起動エラー", f"ファイルを開けませんでした: {exc}")

    def open_output_folder(self) -> None:
        if not self.current_result:
            messagebox.showinfo("未実行", "先に集計を実行してください。")
            return
        try:
            open_path(self.current_result.output_dir)
        except OSError as exc:
            messagebox.showerror("起動エラー", f"フォルダを開けませんでした: {exc}")

    def copy_results(self) -> None:
        if not self.current_result or not self.current_result.summary_rows:
            messagebox.showinfo("未実行", "コピーできる集計結果がありません。")
            return

        lines = ["Aura\tOdds\tCount\tPercentage"]
        for row in self.current_result.summary_rows:
            lines.append(f"{row.aura}\t{row.odds_display}\t{row.count}\t{row.percentage:.2f}")

        payload = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)
        self.status_var.set("集計結果をクリップボードへコピーしました。")

    def run(self) -> None:
        self.root.mainloop()


def launch_gui() -> None:
    AuraCounterGui().run()
