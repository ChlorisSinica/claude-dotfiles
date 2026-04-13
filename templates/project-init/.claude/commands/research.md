---
description: "Phase 1: research.md の作成（プロジェクト全ファイルを分析）"
---

# research.md の作成

## 入力

- `$ARGUMENTS`: 目的の種別（省略可）
  - `開発` or 空 → 開発モード（デフォルト）
  - `不具合` → 不具合調査モード
  - `更新` → 既存 research.md の更新モード

## プロジェクト情報

- **言語/フレームワーク**: {{LANG}}
- **検証コマンド**: `{{VERIFY_CMD}}`
- **優先して読むファイル**: `{{FILE_PATTERNS}}`
- **通常は読まないディレクトリ/パス**: `{{EXCLUDE_DIRS}}`
- **通常は読まないファイルパターン**: `{{EXCLUDE_FILE_PATTERNS}}`

## プロンプト

**（開発）**
`.agents`，`.context`，`.claude`，`.` で始まるフォルダ，`_` で始まるフォルダを除外したうえで，プロジェクト情報に書かれた除外対象は原則として読まず，`{{FILE_PATTERNS}}` に一致する実装本体を優先してじっくり読んでください．ただし，今回のタスクに直接関係する場合だけ例外的に読んで構いません．それが終わったら，学んだことや発見や知っていることを全て詳細にまとめ，`.claude/context/research.md` を日本語で作成してください．

**（不具合）**
プロジェクト全体の潜在的なバグを探してください。すべてのバグを見つけるまで調査を続けてください。終わったら，調査結果の詳細な報告書を `research.md` に専用のセクションとして追加してください．

**（更新）**
既に opus 4.6 が作成した `.claude/context/research.md` が存在する場合は削除せず，レビューも行い，不足分や差分を記述して更新してください．

## 必須分析項目

research.md には以下を**必ず**含めること:

1. **各ファイルの役割と内部実装** — 関数シグネチャだけでなく内部ロジックまで
2. **モジュール間依存グラフ** — import/include/require 関係、相互参照
3. **スクリプト間データフロー** — どの関数が何を引数として受け取り、何を返すか
   - コールバックのシグネチャと呼び出し側の実体の対応
   - 設定値（dict/config/object）の伝播経路（生成 → 加工 → 消費）
   - ファイル I/O の構造（フィールド名と型）
4. **重要な変数の行き来** — 各スクリプト間で受け渡される変数名・型・デフォルト値
   - 特に「ハードコードされている値」と「設定から取得される値」の区別
5. **存在しないが必要なもの** — 呼び出されていないが統合時に必要になるメソッド/パラメータ
6. **潜在的なバグ・リスク** — 事実と推測を区別

## ルール

- Separate facts from guesses. If unsure, mark as "要確認".
- Read actual file contents; never infer from filenames alone.
- "Deeply" means reading function internals, not just signatures.
- `{{EXCLUDE_DIRS}}` と `{{EXCLUDE_FILE_PATTERNS}}` は原則として調査対象外。必要なときだけ例外扱いにすること。
- Do NOT fabricate bugs. If no bugs are found, say so explicitly.
- **言語制約**: このプロジェクトは {{LANG}} です。他の言語のツールやコマンド（例: 別言語のインタプリタ）を実行しないこと。検証が必要な場合は `{{VERIFY_CMD}}` を使用すること。

## 出力

`.claude/context/research.md`

## 次のステップ

`/plan <機能の説明>` で設計に進む
