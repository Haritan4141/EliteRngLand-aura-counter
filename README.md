# Elite's RNG Land Aura Counter

VRChat ワールド「Elite's RNG Land」のログから、`Firing ○○'s cutscene...` と `Firing ○○'s unique cutscene...` を抽出して aura 出現数を集計する Windows 向けツールです。

## 実装方針

- GUI は標準搭載の `tkinter` を採用
  - 依存が軽く、配布しやすいです
- ドラッグ＆ドロップは `tkinterdnd2` を追加
  - `tkinter` 単体では Windows Explorer からの D&D が弱いためです
- exe 化は `PyInstaller`
  - `--windowed` 相当で黒いコンソールを出しません
- ログ解析は標準ライブラリのみ
  - 再帰検索、行単位ストリーム読み込み、CSV 出力で大量ログにも耐えやすい構成です

## 推奨ライブラリ構成

- 必須
  - `tkinter` (Python 標準)
  - `tkinterdnd2`
- ビルド用
  - `pyinstaller`

## ディレクトリ構成

```text
Elite's RNG Land/
├─ assets/
│  ├─ app.ico
│  └─ README.txt
├─ src/
│  └─ elite_rng_land_tool/
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ app.py
│     ├─ backup.py
│     ├─ exporter.py
│     ├─ gui.py
│     ├─ models.py
│     ├─ parser.py
│     ├─ service.py
│     ├─ settings.py
│     ├─ utils.py
│     └─ version.py
├─ build_exe.bat
├─ EliteRngLandAuraTool.spec
├─ requirements.txt
├─ run_local.bat
└─ README.md
```

## 現在の機能

- `.txt` / `.log` の再帰検索
- 複数ログの合算集計
- aura ごとの件数集計
- ファイル別 CSV 出力
- GUI 上での結果一覧表示
- `aura_odds.csv` を読み込んで aura ごとの確率(1/N)を表示
- GUI の初期表示は確率順(1/N の N が大きい順)
- フォルダ選択ボタン
- `自動集計` ボタンで `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat` を即集計
- 起動中に `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat\VRChatLogsBackup` へ 5 分ごとに自動バックアップ
- バックアップ更新時に `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat\VRChatLogsBackup\aura_only` を同時生成
- バックアップ更新時に未対応候補を `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat\VRChatLogsBackup\unknown_aura_patterns.log` へ保存
- `バックアップ集計` ボタンで `VRChatLogsBackup\aura_only` を集計
- `VRChatログを開く` ボタンで `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat` を開く
- 起動時に集計元を `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat` へ自動設定
- 起動時に保存先を `%USERPROFILE%\Documents\Elite's RNG Land\exports` へ自動設定
- バックアップフォルダが無ければ自動生成
- 保存先フォルダが無ければ自動生成
- フォルダのドラッグ＆ドロップ
- `CSVを開く` ボタンから summary CSV を開く
- 保存先フォルダを開く
- 結果コピー
- 重複行除外設定の記憶
- 重複行除外モード
- ヘッダクリックによるソート切替

## 集計ルール

- 対象行:

```text
2026.03.08 03:05:51 Debug      -  [<color=#00EEFF>Elite's RNG Land</color>] [<color=grey>LOG</color>] Firing Diamond's cutscene...
```

- `Firing ○○'s cutscene...` と `Firing ○○'s unique cutscene...` の `○○` を aura 名として抽出します
- `aura_odds.csv` に一致する aura は確率(1/N)を紐付けて表示します
- 同一 aura 名は完全一致で集計します
- GUI の初期表示は確率順(1/N の N が大きい順)です
- 通常の VRChat ログ集計では `VRChatLogsBackup` 配下を除外し、二重計上を防ぎます
- `aura_only` には aura 関連行だけを保持するため、バックアップ集計を軽量化できます
- `unknown_aura_patterns.log` には、現行パターンでは抽出できないが `Elite's RNG Land` または `cutscene` を含む行を記録します
- 一致しない行は無視します

## 文字コードとエラー耐性

- ログは `utf-8-sig`, `utf-8`, `cp932`, `utf-16` 系を順に判定します
- 読み込み不能ファイルがあっても全体処理は継続します
- エラーは `aura_errors.log` に出力します
- CSV は Excel で開きやすい `utf-8-sig` で保存します

## ローカル実行手順

### 1. GUI 起動

```bat
run_local.bat
```

### 2. 直接コマンド実行

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python main.py
```

## CLI 実行例

GUI なしで確認したい場合は CLI でも動作します。

```bat
python main.py --input-dir "%USERPROFILE%\AppData\LocalLow\VRChat\VRChat" --output-dir "%USERPROFILE%\Documents\Elite's RNG Land\exports" --no-open
```

オプション:

- `--dedupe`
  - 完全一致した重複行を同一ファイル内で 1 回として扱います
- `--no-open`
  - 集計後に CSV を自動で開きません

## GUI の使い方

1. `run_local.bat` または exe を起動
2. 起動時に集計元は `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat`、保存先は `%USERPROFILE%\Documents\Elite's RNG Land\exports` に自動設定されます
3. 起動中は `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat\VRChatLogsBackup` へ 5 分ごとに自動バックアップされ、同時に `aura_only` と `unknown_aura_patterns.log` も更新されます
4. `自動集計` を押すと標準ログフォルダをそのまま集計できます
5. `バックアップ集計` を押すと最新化した `aura_only` を集計できます
6. `VRChatログを開く` を押すと同じログフォルダを Explorer で開けます
7. もしくは集計元フォルダをドラッグ＆ドロップ、または `フォルダ選択`
8. 必要なら保存先フォルダを指定
9. 手動指定した場合は `集計開始` を押す
10. GUI の表で結果確認
11. 必要に応じて `CSVを開く` から `aura_summary.csv` を開く

## 出力ファイル

- `aura_summary.csv`
  - `Aura,Count,Odds`
- `aura_summary_detailed.csv`
  - `Aura,Count,Percentage,Odds`
- `aura_summary_by_file.csv`
  - `File,Aura,Count,Odds`
- `aura_errors.log`
  - スキップや読み込み失敗の記録

出力先には毎回タイムスタンプ付きフォルダが作成されます。

例:

```text
exports/
└─ aura_results_20260308_153000/
   ├─ aura_summary.csv
   ├─ aura_summary_detailed.csv
   ├─ aura_summary_by_file.csv
   └─ aura_errors.log
```

## exe ビルド手順

### もっとも簡単な方法

```bat
build_exe.bat
```

### 手動コマンド

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean EliteRngLandAuraTool.spec
```

成果物:

```text
dist\EliteRngLandAuraTool.exe
```

## GitHub Release 手順

### 1. リリース用コミットを確認

```bat
git status
git log --oneline -1
```

### 2. リリースタグ `v1.3.0` を作成

```bat
git tag -a v1.3.0 -m "Release v1.3.0"
```

### 3. GitHub へコミットとタグを push

```bat
git push origin main
git push origin v1.3.0
```

### 4. GitHub Releases を作成

1. GitHub のリポジトリページを開く
2. `Releases` → `Draft a new release`
3. Tag に `v1.3.0` を選択
4. Title を `v1.3.0` にする
5. 説明欄に更新内容を書く
6. `dist\EliteRngLandAuraTool.exe` を添付
7. `Publish release` を押す

### 5. 配布前チェック

1. `dist\EliteRngLandAuraTool.exe` が最新ビルドか確認
2. `assets\app.ico` が本番アイコンか確認
3. `aura_odds.csv` が最新内容か確認
4. 別の Windows 環境で起動確認

## アイコン差し替え方法

1. `assets\app.ico` を本番用アイコンで置き換える
2. Windows 用の実 ICO 形式を使う
3. 推奨は複数サイズ入り
   - `16x16`
   - `32x32`
   - `48x48`
   - `64x64`
   - `128x128`
   - `256x256`
4. PNG を `.ico` にリネームしただけのファイルは不可
5. ファイル名を変えない場合はそのままビルド
6. ファイル名を変える場合は以下を更新
   - `EliteRngLandAuraTool.spec`
   - `src\elite_rng_land_tool\gui.py`

ビルドエラー補足:

- `app.ico` の拡張子でも、中身が PNG だと PyInstaller は失敗します
- `requirements.txt` に `Pillow` を入れてあるので自動変換の余地はありますが、配布向けには実 ICO を推奨します

## 配布時の想定

- 配布対象は `dist\EliteRngLandAuraTool.exe`
- 初回起動時に設定ファイルを `%APPDATA%\EliteRngLandAuraTool\settings.json` へ保存します
- Python 非導入の Windows 環境でも exe 単体で実行できます
- `自動集計`、`バックアップ集計`、`VRChatログを開く` は各ユーザーの `%USERPROFILE%` を使うため、ユーザー名に依存しません
- 起動時の既定保存先 `%USERPROFILE%\Documents\Elite's RNG Land\exports` とバックアップ先 `%USERPROFILE%\AppData\LocalLow\VRChat\VRChat\VRChatLogsBackup`、`aura_only`、`unknown_aura_patterns.log` も各ユーザーごとに自動解決されます

## 補足

- GUI は `tkinterdnd2` が入っていると D&D が有効になります
- PyInstaller ビルド時は `.spec` からアイコンと D&D 依存を取り込みます
- 保存先を毎回分けるので、過去結果を残しやすい構成です
- `aura_odds.csv` は exe 化時にも同梱されます








