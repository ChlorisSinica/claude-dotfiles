# Development Lessons — Cross-Project Knowledge

> skills テンプレート更新時に参照する、プロジェクト横断の教訓集。
> `/update-workflow` や `/codex-impl-review` の改善に反映すべき項目。

---

## 1. Python 構文チェック (codex-impl-review 統合候補)

**問題:** `IndentationError` / `SyntaxError` は Python のパース段階で発生し、
try/except では捕捉できない。ログファイルも作成されず、呼び出し元 (AHK 等) は
「失敗しました」としか報告できない。Codex レビューでも見逃すことがある。

**対策:** `.py` ファイルを Edit/Write した後、Codex 送信前に必ず実行:
```bash
python -c "import py_compile; py_compile.compile('file.py', doraise=True)"
```

**統合先:** `/codex-impl-review` のサイクル開始前ステップに追加。
対象ファイルに `.py` が含まれる場合、全 `.py` に対して `py_compile` を実行。
失敗した場合は Codex に送信せず、即座に修正。

---

## 2. AHK Run で PID 追跡する場合は直接実行

**問題:** `cmd /c python ...` や `powershell -Command python ...` 経由だと、
AHK の `Run, ..., , , PID` が返す PID は中間プロセス (cmd.exe / powershell.exe) を指す。
Python 本体の PID とずれるため、プロセス監視が壊れる。

**対策:** `Run, python script.py args, , , scanPID` で直接起動。
stderr キャプチャが必要な場合は、Python スクリプト内部で `sys.stderr` をファイルにリダイレクト。

---

## 3. tkinter で DPI awareness を設定しない

**問題:** `SetProcessDpiAwareness(1)` や `(2)` を設定すると:
- Win32 API (物理ピクセル) と tkinter geometry (論理ピクセル) の座標系が不整合
- デュアルディスプレイでのドラッグ時にスケール変動
- ウィンドウサイズが意図と異なる

**対策:** DPI awareness は設定せず、Windows のデフォルト DPI 仮想化に任せる。
tkinter と Win32 API が同じ論理ピクセル座標系で動作する。
画像プレビューの品質低下は PIL の `thumbnail()` + `LANCZOS` で十分補える。

---

## 4. リアルタイムインデックス (Everything / WDS) の temp 除外

**問題:** Everything はファイル作成を即座にインデックスする。
一時ディレクトリに展開したファイルが検索候補に含まれ、
自分自身を「ソース」として返す (MD5 も当然一致)。

**対策:**
- Everything: `!path:<dir>` を検索引数に追加 (複数引数で渡す)
- WDS: SQL の `NOT LIKE '<dir>\\%'` を WHERE 句に追加
- `filter_hash_matches()` でセーフティネット (`_is_under_excluded_dir`)

除外対象の典型例:
- `%TEMP%` (一時ファイル全般)
- `%LOCALAPPDATA%\Google\DriveFS\` (Google Drive キャッシュ)
- `<project>_sources\` (エクスポート済みコピー)

---

## 5. マルチ PC 共同作業でのメタデータ保護

**問題:** RETRO_SCAN でタグ付けした SOURCE_PATH は、そのPCでのみ有効なパス。
別 PC で再スキャンすると上書きされ、元の正しいパスが消える。

**対策:** `MATCH_METHOD` タグと `INSERTED_BY` タグで出自を管理:
- `PASTE` (Ctrl+V): 信頼できるソース → 上書きスキップ
- `RETRO_SCAN` + 同一ユーザ@PC → 上書き可 (修正反映)
- `RETRO_SCAN` + 他ユーザ@PC → 上書きスキップ (他PCのパスを保護)

---

## 6. GUI プロセスの終了状態管理

**問題:** GUI (tkinter) はスキャン完了後もウィンドウが開いたまま。
呼び出し元 (AHK) が「PID 終了 = スキャン完了」と判定すると、
GUI が開いている間は永久にポーリングし続ける。

**対策:** ステータスファイルの `done=1` / `cancelled=1` / `stage=エラー` を
PID 監視より先にチェック。PID 監視はフォールバックとしてのみ使用。

GUI 閉じ時の `cancelled=1` 書き込みは、`join()` 後にステータスファイルを
再読み取りし、既に `done=1` や `stage=エラー` で終了していれば上書きしない。

---

## 7. ログの DEBUG フラグ方式 — リリース時に除去しない

**問題:** ログ出力をリリース時に除去すると、仕様追加時に再実装が必要。
除去と再実装の繰り返しで実装漏れやバグが発生しやすい。

**対策:** ログは常にコードに残し、`Enabled` フラグで ON/OFF を切り替える。
```
# AHK の例 (DebugUtil.ahk のチャンネルベース方式)
Debug_CreateChannel("PPT_Spacing", logPath, maxBytes, enabled:=true)
Debug_Log("PPT_Spacing", "event_name", "detail=...")

# Python の例
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug_enabled else logging.WARNING)
```

**設計原則:**
- ログ出力のコードは **常に残す** (削除しない)
- 設定ファイル (INI 等) で `Enabled=0` にすればログ出力を抑制
- ログファイルはサイズ上限 + ローテーション (例: 256KB で `.old.log` にリネーム)
- リリースビルドでも `Enabled=1` にすればデバッグ可能

---

## 8. プロセス間通信 (IPC) 用ステータスファイルの設計

**問題:** 異なるプロセス (AHK ↔ Python) 間でリアルタイムの進捗共有が必要。
ファイルベース IPC は実装が簡単だが、競合・文字化け・部分読み取りが発生しうる。

**設計パターン:**
```
# ステータスファイル (key=value 形式、1 行 1 フィールド)
stage=ソース探索中
message=Everything で候補を検索中
current_index=3
total_items=12
done=0
cancelled=0
```

**書き込み側 (Python):**
- `atomic=False` で直接上書き (アトミック rename だと読み取り側が競合)
- `PermissionError` 時はリトライ (20回 × 50ms)
- 改行をスペースに正規化して 1 行に収める

**読み取り側 (AHK / Python GUI):**
- 150-1000ms 間隔でポーリング
- `encoding="utf-8", errors="replace"` で途中の UTF-8 断裂を許容
- 読み取り失敗 (`PermissionError`) は無視して次のポーリングに委ねる
- パースエラーも無視 (不完全な書き込み途中を読んだケース)

**終了状態の判定:**
- `done=1` → 正常完了
- `cancelled=1` → キャンセル完了
- `stage=エラー` → エラー終了
- これらを PID 監視より **先に** チェック (GUI プロセスは終了状態後も生存しうる)

---

## 9. GUI ログと永続ログの分離

**問題:** ユーザー向けの画面表示 (揮発) と、デバッグ用のファイルログ (永続) は
目的・詳細度・寿命が異なる。混同すると片方が使いにくくなる。

**設計パターン:**

| 種類 | 目的 | 出力先 | 寿命 | 詳細度 |
|------|------|--------|------|--------|
| **GUI ログ** | ユーザーに進捗を伝える | tkinter Text / Label | ウィンドウ寿命 | 簡潔 (1行/イベント) |
| **永続ログ** | 開発者がデバッグに使う | ファイル (.log) | ローテーション付き | 詳細 (変数値・スタックトレース) |
| **IPC ステータス** | プロセス間の状態共有 | ファイル (.status) | スキャン寿命 | 構造化 (key=value) |

**GUI ログの実装例 (tkinter):**
```python
def _log(self, text):
    self._log_text.config(state="normal")
    self._log_text.insert("end", text + "\n")
    self._log_text.see("end")
    self._log_text.config(state="disabled")
```

**永続ログへの同時書き出し:**
GUI ログに表示する内容は永続ログにも書く。逆は不要 (永続ログの詳細は画面に出さない)。
```python
def _log(self, text):
    # GUI に表示
    self._log_text.insert("end", text + "\n")
    # 永続ログにも記録
    logging.info(text)
```

**ログの 3 層を最初から設計に含めることで:**
- リリース時にログコードを除去する必要がない
- 仕様追加時もログ基盤を再実装する必要がない
- ユーザーには簡潔な情報、開発者には詳細な情報を同時に提供
