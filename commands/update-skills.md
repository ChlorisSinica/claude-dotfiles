---
description: "既存プロジェクトの workflow skills を更新し、.claude/context は保持"
---

# Update Skills — 既存プロジェクトの workflow skills 更新

既存プロジェクトの `.claude/commands/` と `.claude/agents/` を更新してください。
`.claude/context/` や project-specific settings は保持します。

## 入力

- `$ARGUMENTS`: プリセット名（省略可）
  - 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`
  - 研究用: `survey-cv`, `survey-ms`

## 手順

1. **テンプレートとプリセットの選択**:
   - `$ARGUMENTS` が `survey-` で始まる場合: テンプレート = `research-survey`
   - それ以外: テンプレート = `project-init`（デフォルト）
   - `$ARGUMENTS` が指定されていればそのプリセットを使用
   - 空の場合: プロジェクト内のファイルを調べて自動検出
     - `.py` → `python`（requirements.txt / pyproject.toml に `torch` があれば `python-pytorch`）
     - `.ts` / `.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → ユーザーに v1 / v2 を確認
     - `.sln` または `.vcxproj` → `cpp-msvc`
     - `.bib` ファイルや `papers/` ディレクトリがある場合 → `research-survey` テンプレートを提案
   - 判断できない場合はユーザーに選択肢を提示して確認

2. **skills-only 更新を実行**:
   ```bash
   bash ~/.claude/scripts/init-project.sh -t <template> <preset> --skills-only -f
   ```

3. **完了報告**:
   スクリプトの出力をそのまま表示し、`.claude/context` を保持したまま skills を更新したことを伝える。

## 注意

- スクリプトが `Template not found` で失敗した場合は `bash ~/claude-dotfiles/setup.sh -f` を実行するよう案内
- 不明なプリセット名はスクリプトがエラーを出力するので、そのまま報告する
- `--skills-only -f` は `.claude/commands/` と `.claude/agents/` のみ更新し、`.claude/context/`、`CLAUDE.md`、`settings.json`、`settings.local.json`、`.gitignore`、`agents/sessions.json` は保持する
