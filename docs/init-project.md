# Init Project

`init-project.py` の仕様と運用です．Claude の `/init-project` と Codex の `$init-project` は，この Python スクリプトを呼び出すショートカットです．

## smart mode

`init-project.py` は manifest（`.claude-dotfiles-managed.json`）の有無で動作モードを自動判定します．

- manifest 無し → 新規作成モード
- manifest 有り → 更新モード（`--update` 相当）

明示する場合は `--update` / `--fresh` を付けます．

## モード一覧

| モード | 指定方法 | 挙動 |
|---|---|---|
| 新規作成 | manifest 無しで実行 | template から全ファイルを展開．template パスに既存 unmanaged ファイルがあると停止 |
| 更新 | manifest 有りで実行（または `--update`） | manifest 管理下のファイルを template から再生成．未管理のユーザーファイルは保持 |
| 強制再作成 | `--fresh` | 未管理ファイルも含めて template パスを全上書き．`context/` `reviews/` `logs/` は保持 |

更新と強制再作成の重要な違い:

- **更新**: 既存の `.claude/commands/*.md` をユーザーが手で書き換えていても保持．manifest に載っているファイルだけを更新
- **強制再作成**: template パスの全ファイルを上書き．手での書き換えは消える．`.claude/context/` / `.agents/context/` / `.agents/reviews/` / `.agents/logs/` / `.claude/logs/` は保持

## preset と template

### preset

言語 / 用途を指定する引数．

| 分類 | preset | 用途 |
|---|---|---|
| 開発 | `python` | Python（pytest） |
| 開発 | `python-pytorch` | Python + PyTorch |
| 開発 | `typescript` | TypeScript / Node |
| 開発 | `rust` | Rust / Cargo |
| 開発 | `ahk` | AutoHotkey v1 |
| 開発 | `ahk-v2` | AutoHotkey v2 |
| 開発 | `cpp-msvc` | C++（MSVC / Visual Studio） |
| 開発 | `unity` | C#（Unity） |
| 開発 | `blender` | Python（Blender） |
| 研究 | `survey-cv` | Computer Vision 分野の survey |
| 研究 | `survey-ms` | 材料科学分野の survey |

### template 自動選択

- `survey-*` preset → `research-survey` template
- それ以外 → `project-init` template
- `-t codex-main` を付けると Codex 主体 template に切り替え

### preset 別の検証ツール

`init-project.py` は preset に合わせて `.claude/scripts/run-verify.py` 用の設定を生成します．検証を実行するには preset ごとの外部ツールが必要です．

| preset | 検証コマンド | 追加で必要なツール |
|---|---|---|
| `python`, `blender` | `python -m pytest` | Python 3.x，pytest |
| `python-pytorch` | `python -m pytest` + `torch` import | Python，pytest，PyTorch |
| `typescript` | `npx tsc --noEmit && npm test` | Node，npm |
| `rust` | `cargo check && cargo test` | Rust toolchain |
| `ahk` | AutoHotkey v1 の `/ErrorStdOut` | AutoHotkey v1（`C:\Program Files\AutoHotkey\AutoHotkey.exe`） |
| `ahk-v2` | AutoHotkey v2 の `/ErrorStdOut` | AutoHotkey v2（`C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe`） |
| `cpp-msvc`, `unity` | `msbuild` | Visual Studio / MSVC |
| `survey-cv`, `survey-ms` | 検証無し | — |

`project-init` template では，保存時の構文チェック用 `.claude/hooks/syntax-check.py` が preset に応じて生成されます．対象は `python` / `python-pytorch` / `ahk` / `ahk-v2` / `blender`．`typescript` / `rust` / `cpp-msvc` / `unity` では生成されません．`codex-main` と `research-survey` の template では syntax check フックは生成されません．

## 保持されるファイル

`--update` と `--fresh` の両方で保持（上書きしない）されるディレクトリ:

- `.claude/context/`
- `.agents/context/`
- `.agents/reviews/`
- `.agents/logs/`
- `.claude/logs/`
- `.claude/agents/sessions.json`

`--update` ではこれに加え，template パスの**未管理**ファイル（ユーザーが手で作成 / 書き換えたもの）も保持されます．`--fresh` ではこれらも上書きされます．

## エラー別対処

### 既存ファイルとの衝突（InitCollisionError）

manifest 無しで実行したとき，template が展開しようとする位置に unmanaged な既存ファイルがあると停止します（新規作成時に黙って上書きしないため）．典型例は manifest が導入される前に作成されたプロジェクト．

復旧手段:

1. `python ~/.claude/scripts/init-project.py <preset> --fresh` で全上書き（`context/` / `reviews/` / `logs/` は保持される）
2. または衝突しているファイルを手で退避・削除してから `python ~/.claude/scripts/init-project.py <preset>` を再実行

エラーメッセージに衝突ファイルが列挙されます．

### preset 不一致（終了コード 3）

既存 manifest に記録された preset と，今回指定した preset が異なると警告で停止．

対処:

- `--accept-preset-change` で対話なしに承認
- または `--fresh` で一から作り直し

### 旧形式 manifest の template 推定不能

manifest は存在するが template を特定できない場合（古い manifest 形式）:

```
ERROR: legacy manifest detected but template cannot be inferred.
```

対処: `-t <template> <preset>` を 1 回明示して manifest を移行．

### 別 template への切り替え

既存プロジェクトの template を別のものに切り替えようとすると:

```
ERROR: cross-template switch is not supported.
```

対処: 残したい `context/` / `reviews/` を退避してから `.claude/` と `.agents/` を削除し，目的 template で再作成．

### manifest が壊れている

JSON が壊れている場合，非 `--fresh` モードは停止します．`--fresh` は manifest パースエラーを無視して一から作り直すため，復旧パスとして使えます．

## 引数省略による更新

manifest がある既存 project では引数省略でも更新できます．manifest に記録された preset と template が使われます．

```text
python ~/.claude/scripts/init-project.py  # manifest から preset / template を復元して更新
/init-project                            # Claude Code からのショートカット
$init-project                            # Codex からのショートカット
```

## 呼び出し方の使い分け

- **Python 直接呼び出し**: どの環境からでも使える正規の呼び出し
- **Claude Code の `/init-project`**: 3 つの template すべてに対応するショートカット
- **Codex の `$init-project`**: `codex-main` 専用のショートカット．他 template は Python か Claude Code から

```text
python ~/.claude/scripts/init-project.py <preset>                # project-init template（既定）
python ~/.claude/scripts/init-project.py -t codex-main <preset>  # codex-main template を明示
python ~/.claude/scripts/init-project.py survey-cv               # research-survey template（自動判定）
python ~/.claude/scripts/init-project.py <preset> --update       # 更新を明示
python ~/.claude/scripts/init-project.py <preset> --fresh        # 強制再作成
```

`python` の箇所は環境に応じて `python3` / `py -3` に置き換え．

## 関連ページ

- [Claude Workflow](./claude-workflow.md) — 生成後の Claude Code 開発フロー
- [Codex Workflow](./codex-workflow.md) — 生成後の Codex 主体の開発フロー
- [Research Survey](./research-survey.md) — `research-survey` template のフロー
