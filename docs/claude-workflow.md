# Claude Workflow

Claude Code 主体でこの dotfiles を使うときの起点と運用メモです．

## セットアップ

```bash
git clone https://github.com/ChlorisSinica/claude-dotfiles.git ~/claude-dotfiles  # リポジトリ取得
python ~/claude-dotfiles/scripts/setup.py                                         # Claude 用を配布
```

更新時:

```bash
cd ~/claude-dotfiles
git pull
python scripts/setup.py     # 新規ファイルのみコピー
python scripts/setup.py -f  # 管理下のファイルを上書き更新
```

`python` は例です．環境に応じて `python3` や `py -3` など，Python 3.11+ のコマンドに置き換えてください．

## 主な呼び出し

`/init-project` は **smart mode** の唯一の呼び出しコマンドです．旧 `/update-workflow` / `/update-skills` は統合・削除されました．

新規プロジェクト:

```text
/init-project python-pytorch
```

既存プロジェクトの workflow 更新（smart mode で自動遷移）:

```text
/init-project python-pytorch            # preset 確認付きで更新
/init-project                           # preset を manifest から復元
/init-project --update python-pytorch   # 更新を明示（manifest 無ならエラー）
```

## `/init-project` 概要

- 既定テンプレートは `project-init`
- `survey-cv`, `survey-ms` は preset 名から `research-survey` を自動推論
- `-t codex-main` で Codex-first テンプレートを Claude Code から呼べる
- smart mode: manifest 有りなら更新，無しなら新規作成
- `--fresh` で全上書きの強制再作成（未管理ファイルも上書きされる）
- preset 不一致の検出時は終了コード 3．`--accept-preset-change` で承認

例:

```text
/init-project python                                    # 新規作成または既存更新
/init-project survey-cv                                 # research-survey preset
/init-project -t codex-main python                      # Codex-first 新規
/init-project python --fresh                            # 強制再作成
/init-project python-pytorch --accept-preset-change     # preset 差し替え承認
```

生成直後の注意:

- 新しく展開された `.claude/commands/` や `.agents/skills/` は，起動中の Claude Code / Codex セッションには即時反映されないことがある
- 使えない場合は一度セッションを開き直すか，アプリを再起動する

## ワークフロー更新

`/init-project` が smart mode で自動的に更新モードへ遷移します．従来の `/update-workflow` と同じ挙動です:

- `.claude/context/` と runtime state を保持しつつ，template-managed files を更新
- `-t codex-main` では `.agents/context/` と `.agents/reviews/` を保持しつつ Codex-first asset を更新
- 既存プロジェクト（manifest 有）で `/init-project` を単独で打てば preset も manifest から復元

## 開発ワークフロー

Claude Code 主体で進めるときの基本フロー:

```text
/init-project → /research → /plan → /sonnet-dp-research（省略可）
              → /codex-plan-review → /implement → /codex-impl-review
              → /handover, /retro
```

補足:

- `/sonnet-dp-research` は Discussion Point が残ったときだけ挟む
- `/codex-plan-review` と `/codex-impl-review` には Codex CLI が必要
- 小さな変更では `/research` や `/handover`, `/retro` を省略してよい

前提:

- Codex CLI: `npm install -g @openai/codex`
- `codex-plugin-cc` は `/codex:review` などの汎用レビューを使う場合に推奨

## Claude 側の自動承認

この節は `.claude/settings.local.json` を使う workflow 向けです．

`/init-project` 実行時に `.claude/settings.local.json.bak` が生成されます．必要なときだけ有効化してください．

```bash
cd /path/to/your/project

# ON
mv .claude/settings.local.json.bak .claude/settings.local.json

# OFF
mv .claude/settings.local.json .claude/settings.local.json.bak
```

注意:

- `Bash(git *)` や `Bash(*)` のような広い許可は避ける
- `git push` は手動承認のまま維持する
- 検証コマンドの許可候補は preset に応じて自動生成される

## Claude から Codex を使う場合

`codex-plugin-cc` は Claude Code から `/codex:*` を使う場合に便利です．

```text
/plugin marketplace add openai/codex-plugin-cc  # marketplace を追加
/plugin install codex@openai-codex              # plugin を導入
/reload-plugins                                 # Claude Code を reload
/codex:setup                                    # 初期セットアップ
```

## 関連ページ

- [Codex Workflow](./codex-workflow.md)
- [Research Survey](./research-survey.md)
- [Windows Terminal](./windows-terminal.md)
- [Statusline](./statusline.md)
