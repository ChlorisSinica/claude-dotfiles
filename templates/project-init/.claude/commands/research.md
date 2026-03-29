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

## プロンプト

**（開発）**
`.agents` と `.context` と `.claude` 以外のこのプロジェクトのファイルを全てじっくり読み，仕組みや役割，そしてすべての特徴を深く理解してください．それが終わったら，学んだことや発見や知っていることを全て詳細にまとめ，`.claude/context/research.md` を日本語で作成してください．

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
- Do NOT fabricate bugs. If no bugs are found, say so explicitly.
- **言語制約**: このプロジェクトは {{LANG}} です。他の言語のツールやコマンド（例: 別言語のインタプリタ）を実行しないこと。検証が必要な場合は `{{VERIFY_CMD}}` を使用すること。

## 出力

`.claude/context/research.md`

## 次のステップ

`/codex-research-review` で Codex レビューを実行
