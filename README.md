# Claude Code Dotfiles

Claude Code × Codex 連携ワークフローのグローバル設定．

## 早見表

- Claude Code 主体で使う: [Claude Workflow](./docs/claude-workflow.md)
- Codex 主体で使う: [Codex Workflow](./docs/codex-workflow.md)
- 研究サーベイ用: [Research Survey](./docs/research-survey.md)
- Windows Terminal 補助: [Windows Terminal](./docs/windows-terminal.md)
- ステータスライン: [Statusline](./docs/statusline.md)

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles
python ~/claude-dotfiles/scripts/setup.py
```

Codex 用の global skills も入れる場合:

```bash
python ~/claude-dotfiles/scripts/setup.py --codex
```

既存の Claude / Codex 用ファイルを上書き更新する場合:

```bash
python ~/claude-dotfiles/scripts/setup.py -f --codex
```

> **注意**: `python` は例です．環境に応じて `python3` や `py -3` など，Python 3.11+ の launcher に置き換えてください．

`~/.claude/` に以下がインストールされます:

- `commands/init-project.md` — `/init-project` グローバルコマンド（smart mode で init / update を自動判定）
- `templates/project-init/` — 開発プロジェクト初期化テンプレート
- `templates/research-survey/` — 研究サーベイ用テンプレート
- `templates/codex-main/` — Codex-first プロジェクト用テンプレート
- `scripts/init-project.py` — `codex-main` のテンプレート展開スクリプト本体
- `scripts/setup.py` — Python ベースの install / sync エントリポイント
- `scripts/survey-convert.py` — Markdown → LaTeX 変換スクリプト

`setup.py --codex` を使うと，さらに `~/.codex/skills/` に以下の global skill が入ります:

- `init-project` — Codex skill．`codex-main` scaffold の作成・更新（smart mode）を担う．内部で `~/.claude/scripts/init-project.py -t codex-main <preset>` を呼ぶ

また，既知の plugin manifest warning を減らすために `fix_codex_plugin_prompts.py` を best-effort で実行します．

初回導入は `python ~/claude-dotfiles/scripts/setup.py --codex` で十分です．`-f` は既存ファイルを上書き更新したいときだけ使用してください．

## グローバル設定の更新

```bash
cd ~/claude-dotfiles
git pull
python scripts/setup.py             # Claude 用の新規ファイルのみコピー
python scripts/setup.py -f          # Claude 用ファイルを上書き更新
python scripts/setup.py --codex     # Claude + Codex 用の新規ファイルのみコピー
python scripts/setup.py -f --codex  # Claude + Codex 用ファイルを上書き更新
```

## 使い方

`setup.py` と `init-project.py` は **Python script が実体**．Python を直接叩くのが基本．Claude Code の slash command（`/init-project`）と Codex の skill（`$init-project`）は同じ Python script を呼ぶ薄いラッパー．どこから起動しても最終的に同じコードが実行される．

### コマンド対応表

`/init-project`（Claude）と `$init-project`（Codex）は内部で `init-project.py` を呼ぶ．**smart mode** で新規 scaffold と既存 workflow update を manifest 検出により自動判定．旧 `/update-workflow` / `/update-skills` / `$update-workflow` は Bundle 2 で削除済．

| 操作 | Python（実体） | Claude Code | Codex |
|---|---|---|---|
| 新規 scaffold（project-init，default） | `python ~/.claude/scripts/init-project.py <preset>` | `/init-project <preset>` | — |
| 新規 scaffold（codex-main） | `python ~/.claude/scripts/init-project.py -t codex-main <preset>` | `/init-project -t codex-main <preset>` | `$init-project <preset>` |
| 新規 scaffold（research-survey） | `python ~/.claude/scripts/init-project.py survey-cv` | `/init-project survey-cv`（preset 名から自動判定）| — |
| workflow 更新（smart） | `python ~/.claude/scripts/init-project.py <preset>`（manifest 有で update に遷移） | `/init-project <preset>` | `$init-project <preset>` |
| workflow 更新を明示 | `python ~/.claude/scripts/init-project.py <preset> --update` | `/init-project <preset> --update` | `$init-project <preset> --update` |
| 強制 re-init（全上書き） | `python ~/.claude/scripts/init-project.py <preset> --fresh` | `/init-project <preset> --fresh` | `$init-project <preset> --fresh` |

- Codex skill は codex-main 専用．project-init / research-survey は Python 直叩き or Claude Code 経由で．
- preset mismatch 検出時は exit code 3．`--accept-preset-change` で非対話承認．
- 既存 scaffold で別 template に切り替えるには手動で `rm -rf .claude .agents` してから再 init．

構成は 3 層：

- **Python 本体**（実体）: `~/.claude/scripts/init-project.py` が scaffold / update を実行する正規実装
- **ラッパー**（任意）: Claude Code の `/init-project` と Codex の `$init-project` は上記 Python を呼ぶ薄い呼び出し
- **repo-local workflow**: `codex-main` 生成後は `.agents/skills/`, `.agents/prompts/`, `.agents/context/`, `.agents/reviews/` を使う．review / verify の機械処理は `scripts/run-codex-*.py`, `scripts/run-verify.py` が担う

Python 直実行時のパス表記:

- `~/.claude/...` はホームディレクトリ配下を指す（Windows では `C:\Users\<user>\.claude\...`）
- `/.claude/...` は Windows で `C:\.claude\...` になってしまうため使わない
- 明示パスにしたい場合は `C:\Users\CVSLab\.claude\scripts\init-project.py` のように書く

### Python から実行（実体・基本）

```
python ~/.claude/scripts/init-project.py python                  # 新規 or 既存 refresh（smart, default = project-init）
python ~/.claude/scripts/init-project.py                         # manifest 有なら preset 復元で refresh
python ~/.claude/scripts/init-project.py -t codex-main python    # codex-main scaffold を明示
python ~/.claude/scripts/init-project.py python --update         # update mode 強制
python ~/.claude/scripts/init-project.py python --fresh          # 全 overwrite で再 init
```

`python` は例．環境に応じて `python3` や `py -3` など Python 3.11+ launcher に置き換える．

### Claude Code から呼ぶ場合（ラッパー）

```
/init-project python-pytorch                # 新規 or 既存 refresh（smart）
/init-project                               # manifest 有なら preset 復元で refresh
/init-project python-pytorch --update       # update mode 強制
/init-project python-pytorch --fresh        # 全 overwrite で再 init
```

### Codex から呼ぶ場合（ラッパー）

```
$init-project python                        # 新規 or 既存 refresh（smart, codex-main）
$init-project                               # manifest 有なら preset 復元で refresh
$init-project python --update               # update 強制
$init-project python --fresh                # 全 overwrite で再 init
```

生成される主な資産（template 別）:

- **共通**（全 template）: `.claude/settings.json`, `.claude/settings.local.json(.bak)`, `scripts/run-verify.py`, `scripts/verify-config.json`, `.gitignore`
- **codex-main 固有**: `.agents/AGENTS.md`, `.agents/skills/`, `.agents/prompts/`, `.agents/context/`, `.agents/reviews/`, `scripts/run-codex-plan-review.py`, `scripts/run-codex-impl-review.py`, `scripts/run-codex-impl-cycle.py`, `scripts/fix_codex_plugin_prompts.py`
- **project-init / research-survey 固有**: `.claude/CLAUDE.md`, `.claude/commands/`, `.claude/agents/`, `.claude/hooks/syntax-check.py`

`/init-project` の smart update は `.claude/context/`，`.agents/context/`，`.agents/reviews/`，`.claude/agents/sessions.json` を保持しつつ，template-managed files と generated workflow files（`.claude/CLAUDE.md`，`.claude/settings.json`，`.claude/settings.local.json`，`.claude/hooks/syntax-check.py`，`.gitignore` を含む）を更新します．

新しく展開された repo-local commands / skills は，起動中の Claude Code / Codex セッションには即時反映されないことがあります．使えない場合は一度セッションを開き直すか，アプリを再起動してください．

### Codex-first の最短フロー

初回セットアップ:

```bash
python ~/claude-dotfiles/scripts/setup.py --codex
```

新規プロジェクトを Codex-first で初期化:

```text
$init-project ahk
```

`$init-project` は Codex skill の呼び出し名．実体は Python script `~/.claude/scripts/init-project.py -t codex-main <preset>` で，この skill はそれを呼ぶラッパー．

既存プロジェクトの `.agents` workflow asset を更新:

```text
$init-project ahk     # smart mode: manifest 検出 → update に自動遷移
$init-project         # preset も manifest から復元（引数省略）
```

初期化後に使う repo-local skill（Codex から `$<name>` で呼ぶ）:

- `.agents/skills/codex-research` — コードベース調査
- `.agents/skills/codex-plan` — plan/tasks 作成
- `.agents/skills/codex-plan-review` — plan/tasks の収束レビュー
  中間結果は `.agents/context/codex_plan_*.md`，共有用結果は `.agents/reviews/` に保存
- `.agents/skills/codex-implement` — 実装と検証
  drift audit，verify wrapper fallback，runtime の boundary-based triage を含む
- `.agents/skills/codex-impl-review` — 実装変更の収束レビュー
  `.agents/context/_codex_input.tmp` に入力を束ね，中間結果は `.agents/context/codex_impl_review.md` に保存
- `.agents/skills/codex-fkin-impl-cycle` — task-slice 実装と phase-aware review cycle の自動周回（alignment → verification → quality を Python runner で収束）
- `.agents/skills/handover-skills` — 長い cycle の handover 整理
- review runner は `python scripts/run-codex-*.py ...` で実行する
- review runner の `codex review` 実行には既定で 600 秒の timeout がある．長い review だけ `--review-timeout-sec <seconds>` で延長できる
- review runner は 1 実行 = 1 cycle の機械処理だけを担う
- `.agents/skills/codex-review` — 単発レビュー
- `.agents/skills/sonnet-dp-research-bridge` — 必要時のみ Claude / Sonnet へ人力委譲

Codex-first の基本フロー:

```text
$init-project → $codex-research → $codex-plan
              → $codex-plan-review
              → $sonnet-dp-research-bridge（必要時のみ）
              → $codex-implement → $codex-impl-review
```

補足:

- `$<name>` は Codex から呼ぶ skill 名（例: `$codex-research`）
- `codex-main` の実ファイル生成は `init-project.py` が担当
- `codex-main` の review 系は `.agents/skills/*` と `.agents/prompts/*` を使う運用で，Claude Code の `/...` コマンドとは別系統
- Windows で `codex-plan-review` / `codex-impl-review` の runner を更新したい場合は `python ~/.claude/scripts/init-project.py --update` か `/init-project --update` を使うと，plugin prompt warning の自動補正，`windows.sandbox="unelevated"` への fallback，`--review-timeout-sec` 対応，末尾 `VERDICT:` の厳格判定が反映される

## codex-plugin-cc のインストール（Claude Code から `/codex:*` を使う場合に推奨）

`/codex:review`（汎用レビュー）や `/codex:adversarial-review` を使う場合に推奨です．Claude Code のチャット内で以下を実行してください:

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

Codex CLI が未インストールの場合は `/codex:setup` が自動インストールを提案します．未ログインの場合は `! codex login` を実行してください．

## ワークフロー

### Claude Code の開発ワークフロー

```
/init-project → /research → /plan → /sonnet-dp-research（省略可
              → /codex-plan-review → /implement → /codex-impl-review
              → /handover, retro
```

**前提**: Codex CLI (`npm install -g @openai/codex`) が必要です．codex-plugin-cc は `/codex:review`（汎用レビュー）を使う場合に推奨です．

### 研究サーベイワークフロー

```
/init-project survey-cv → /scope <topic>
                        → /search → /read → /outline
                        → /draft → /review → /convert
```

**前提**: `/convert` には Pandoc が必要です（`winget install --id JohnMacFarlane.Pandoc`）．

## 開発プリセット

- 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`
- 研究用: `survey-cv`, `survey-ms`

## 詳細ドキュメント

- [Claude Workflow](./docs/claude-workflow.md)
- [Codex Workflow](./docs/codex-workflow.md)
- [Research Survey](./docs/research-survey.md)
- [Windows Terminal](./docs/windows-terminal.md)
- [Statusline](./docs/statusline.md)
