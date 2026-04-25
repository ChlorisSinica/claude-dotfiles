---
description: "プロジェクトに Claude Code × Codex 連携環境をセットアップ（新規 init / workflow update を smart mode で自動判定）"
---

# Init Project — Claude Code × Codex 連携環境のセットアップ

`/init-project` は **smart mode** で動作します．既存の scaffold manifest が有れば workflow update，無ければ fresh init．旧 `/update-workflow` と `/update-skills` はこのコマンドに統合されました．

## 入力

- `$ARGUMENTS`: プリセット名（省略可）
  - 開発用: `python`, `python-pytorch`, `typescript`, `rust`, `ahk`, `ahk-v2`, `cpp-msvc`, `unity`, `blender`
  - 研究用: `survey-cv`, `survey-ms`
- `-t codex-main` — Codex 主体テンプレートを明示選択
- `--update` — smart 判定を無視して update mode 強制（manifest 無なら ERROR）
- `--fresh` — smart 判定を無視して fresh init 強制（全ファイル overwrite の nuclear option）
- `--accept-preset-change` — preset mismatch 時の非対話承認

## 手順

1. **preset の決定**:
   - `$ARGUMENTS` が指定されていればそれを使用
   - 空の場合: プロジェクト内ファイルを調べて自動検出
     - `.py` → `python`（requirements.txt / pyproject.toml に `torch` があれば `python-pytorch`）
     - `.ts` / `.tsx` → `typescript`
     - `.rs` → `rust`
     - `.ahk` → ユーザーに v1 / v2 を確認
     - `.sln` または `.vcxproj` → `cpp-msvc`
     - `.unity` または `Assets/` + `ProjectSettings/` → `unity`
     - `.blend` → `blender`
     - `.bib` ファイルや `papers/` ディレクトリ → research-survey を提案
   - 判断できない場合はユーザーに選択肢を提示して確認

2. **template の決定**:
   - `-t` 明示があればそれを使う
   - 空 + preset が `survey-` prefix → `research-survey`
   - 空 + 上記以外 → `project-init`（デフォルト）

3. **スクリプト実行**:
   ```text
   <python-launcher> ~/.claude/scripts/init-project.py [-t <template>] <preset> [flags]
   ```
   `<python-launcher>` には `python`, `python3`, `py -3` など Python 3.11+ launcher．

   具体的ケース:
   - 新規プロジェクト（`.claude/` / `.agents/` 無）:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py <preset>
     ```
     例: `python ~/.claude/scripts/init-project.py python-pytorch`
   - 既存 scaffold の workflow 更新（manifest 有、smart mode で update）:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py
     ```
     preset は manifest から復元．引数省略可．
   - 既存 repo の workflow 明示更新:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py --update
     ```
   - 強制 re-init（全 overwrite）:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py <preset> --fresh
     ```
   - Codex 主体 template:
     ```text
     <python-launcher> ~/.claude/scripts/init-project.py -t codex-main <preset>
     ```

   `~/.claude/...` を使うこと．`/.claude/...` は Windows では `C:\.claude\...` になるので使わない．

4. **エラー対応**:
   - exit code 3（preset mismatch）: ユーザーに「manifest preset と引数 preset が異なる」旨を伝え，承認を得てから `--accept-preset-change` 付きで再実行（または `--fresh` で完全やり直し）
   - exit code 1（`Template not found` 等）: `<python-launcher> ~/claude-dotfiles/scripts/setup.py --codex -f` を案内（codex-main で失敗時），または `setup.py -f` 単体（standard template で失敗時）
   - legacy manifest エラー「template cannot be inferred」: ユーザーに `-t <template> <preset>` を 1 回明示してもらい manifest を migrate

5. **完了報告**:
   スクリプトの出力をそのまま表示し，次のステップを案内する．

## 注意

- **smart mode の優先順位**: `--fresh` > `--update` > manifest 有（→ update）> manifest 無（→ init）
- **preset 省略時**: manifest が有れば自動復元．無ければエラー（Python CLI）．slash command 側で auto-detect を試みる
- **template switch 非サポート**: 既存 scaffold が `project-init` の repo で `-t codex-main` 指定すると cross-template switch error．切替には手動で `rm -rf .claude .agents` → 再 init
- **新しく展開された repo-local commands / skills は，起動中の Claude Code / Codex セッションには即時反映されないことがある**．必要ならセッションを開き直す or 再起動を案内
- `-t codex-main` は `.agents/skills/` と `.agents/context/` を主軸としたテンプレートを生成し，Python review runner `.agents/scripts/run-codex-*.py`，`.claude/scripts/run-verify.py`，Codex ランタイム設定 `.claude/settings.json` / `.claude/settings.local.json(.bak)` を出力する
- update mode は managed files を refresh しつつ `.claude/context/` / `.agents/context/` / `.agents/reviews/` / `.claude/agents/sessions.json` を preserve
- `--fresh` は非 managed な既存ファイル（template path に user が手動作成した `.claude/settings.json` 等）も overwrite する nuclear option
