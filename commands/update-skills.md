---
description: "互換 alias: /update-workflow を使用して workflow files を更新"
---

# Update Skills — 互換 Alias

このコマンドは `/update-workflow` の互換 alias です。
今後は `/update-workflow` を優先してください。

既存プロジェクトの workflow-managed files を更新してください。
テンプレートに応じた context と runtime state は保持します。

## 入力

- `$ARGUMENTS`: プリセット名（省略可）
  - 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`
  - 研究用: `survey-cv`, `survey-ms`
- 必要に応じて `--codex-main` を付けて Codex 主体テンプレートを更新可能

## 手順

1. `/update-workflow` と同じルールでテンプレートとプリセットを選択する

2. 次を実行する:
   ```bash
   bash ~/.claude/scripts/init-project.sh -t <template> <preset> --workflow-only -f
   ```
   Codex 主体テンプレートの場合:
   ```bash
   bash ~/.claude/scripts/init-project.sh --codex-main <preset> --workflow-only -f
   ```

3. スクリプトの出力をそのまま表示し、テンプレートに応じたローカル作業資産を保持したまま workflow files を更新したことを伝える

## 注意

- スクリプトが `Template not found` で失敗した場合は `bash ~/claude-dotfiles/setup.sh -f` を実行するよう案内
- `--workflow-only` は `--skills-only` の後方互換を含む正式名
