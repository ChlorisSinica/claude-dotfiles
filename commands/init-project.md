---
description: "プロジェクトに Claude Code × Codex 連携環境をセットアップ"
---

# Init Project — Claude Code × Codex 連携環境のセットアップ

## 入力

- `$ARGUMENTS`: 言語プリセット名（省略可）
  - `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`

## 手順

1. **プリセット選択**:
   - `$ARGUMENTS` が指定されていればそのプリセットを使用
   - 空の場合: プロジェクト内のファイル拡張子を調べて自動検出
     - `.py` → `python`（requirements.txt / pyproject.toml に `torch` があれば `python-pytorch`）
     - `.ts` / `.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → ユーザーに v1 / v2 を確認
     - `.sln` または `.vcxproj` → `cpp-msvc`
   - 判断できない場合はユーザーに選択肢を提示して確認

2. **スクリプト実行**:
   ```bash
   bash ~/.claude/scripts/init-project.sh <preset>
   ```
   強制上書きする場合:
   ```bash
   bash ~/.claude/scripts/init-project.sh <preset> -f
   ```

3. **完了報告**:
   スクリプトの出力をそのまま表示し、次のステップを案内する。

## 注意

- スクリプトが `Template not found` で失敗した場合は `bash ~/claude-dotfiles/setup.sh` を実行するよう案内
- 不明なプリセット名はスクリプトがエラーを出力するので、そのまま報告する
