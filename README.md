# Claude Code Dotfiles

Claude Code と Codex の global dotfiles を配布するリポジトリ．実体は 2 つの Python スクリプト:

- `scripts/setup.py` — global install
- `scripts/init-project.py` — プロジェクト雛形の作成と更新

雛形は用途別に 3 種: `project-init`（Claude 主体），`codex-main`（Codex 主体），`research-survey`（研究）．

## セットアップ

前提: Python 3.11+（`python` / `python3` / `py -3` のいずれか）．

```bash
# リポジトリ取得（初回のみ）
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles

# 用途に応じて 1 行を選ぶ（フラグは組み合わせ可）
python ~/claude-dotfiles/scripts/setup.py               # Claude 用のみ配布
python ~/claude-dotfiles/scripts/setup.py --codex       # Codex 用スキルも配布
python ~/claude-dotfiles/scripts/setup.py --statusline  # statusline スクリプトも配布
python ~/claude-dotfiles/scripts/setup.py -f            # 既存ファイルを上書き更新
```

- 初回に `--codex` を付けると `~/.codex/skills/` にも配布．以降はその install を自動で検出するので `--codex` を省略しても同期される
- `-f` は「この dotfiles が管理しているファイル」を上書き．未管理のユーザーファイルは触らない
- 更新時は `git pull` してから同じコマンドを再実行
- `python` は例．環境に応じて `python3` / `py -3` に置き換え

## 呼び出し方

`/init-project`（Claude）／ `$init-project`（Codex）／ Python 直接呼び出しの 3 経路．いずれも実体は `~/.claude/scripts/init-project.py`．

| 経路 | 対応する template |
|---|---|
| `/init-project <preset>` | 3 種すべて（`-t codex-main` で明示切替可） |
| `$init-project <preset>` | `codex-main` 専用 |
| `python ~/.claude/scripts/init-project.py ...` | 3 種すべて |

`survey-cv` / `survey-ms` は preset 名から `research-survey` が自動選択されます．manifest のある既存プロジェクトで引数を省略すると，manifest に記録された preset で更新が走ります．

Windows では `/.claude/...` と書くと `C:\.claude\...` と解釈されるので，`~/.claude/...` か絶対パスを使ってください．

## template と前提ツール

- `project-init`（既定）: Claude Code 主体．`.claude/CLAUDE.md`，`.claude/commands/`，`.claude/agents/`，検証設定を生成
- `codex-main`: Codex 主体．`.agents/AGENTS.md`，`.agents/{skills,prompts,context,reviews}/`，review runner（`scripts/run-codex-*.py`）を生成
- `research-survey`: `survey-*` preset 用．`/scope` → `/search` → `/read` → `/outline` → `/draft` → `/review` → `/convert` のフロー

追加で必要なツールは用途別:

- **雛形の作成のみ**: Python 3.11+ だけで足ります
- **`codex-main` の review runner や Claude 側の `/codex:*` 系コマンド**: Codex CLI（`npm install -g @openai/codex`）
- **`research-survey` の `/convert`**: Pandoc（`winget install --id JohnMacFarlane.Pandoc`）
- **生成された `scripts/run-verify.py` の実行**: preset 依存．TypeScript なら Node，Rust なら Cargo，AutoHotkey なら AHK，C++ / Unity なら MSVC．一覧は [Init Project](./docs/init-project.md)

## `/init-project` の最小理解

- **smart mode**: manifest（`.claude-dotfiles-managed.json`）の有無で新規作成 / 更新を自動判定
- **`--fresh` は未管理ファイルも含めて全上書き**する強制再作成．手で書き換えた `.claude/commands/*.md` 等は消える．ただし `.claude/context/` / `.agents/context/` / `.agents/reviews/` / `.claude/logs/` / `.agents/logs/` は常に保持される
- **別 template への切り替えは非対応**．`project-init` と `codex-main` を行き来するときは，残したい `context/` / `reviews/` を退避してから `.claude/` / `.agents/` を削除し，目的 template で再作成
- **よくある詰まりどころ**:
  - manifest 無しの既存プロジェクトで `.claude/` や `.agents/` のファイルと衝突 → `--fresh` で上書きするか，衝突しているファイルを手で退避
  - preset 不一致（終了コード 3）→ `--accept-preset-change` か `--fresh`
  - 新しく展開されたコマンド / スキルは，起動中のセッションに即時反映されないことがある．必要ならセッションを開き直す

詳細は [Init Project](./docs/init-project.md)．

## さらに読む

- [Init Project](./docs/init-project.md) — `/init-project` の仕様，モード，エラー対処，preset 別の検証ツール
- [Claude Workflow](./docs/claude-workflow.md) — Claude Code 主体の日常フロー
- [Codex Workflow](./docs/codex-workflow.md) — Codex 主体の日常フロー，プロジェクト内スキル一覧
- [Research Survey](./docs/research-survey.md) — `research-survey` template のフロー
- [Windows Terminal](./docs/windows-terminal.md)
- [Statusline](./docs/statusline.md)
