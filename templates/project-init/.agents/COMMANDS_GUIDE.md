# Claude Code × Codex 連携コマンドガイド

## 概要

Claude Code のスラッシュコマンドと Codex プロンプトテンプレートを使い、プロジェクトの分析・設計・実装・レビュー・引き継ぎ・振り返りを効率化します。

---

## 全体の流れ

```
Phase 1:  /research                  ← research.md 作成（Claude が全ファイル分析）
Phase 1b: /codex-research-review     ← Codex レビュー（1サイクルのみ）
Phase 2:  /plan <機能の説明>          ← plan.md + tasks.md 作成（Claude が設計）
Phase 3:  Annotation cycle           ← 人間がインラインコメントで修正指示
Phase 4:  /codex-plan-review         ← Codex クロスレビュー（APPROVED まで繰り返し）
Phase 5:  /implement [タスク番号]     ← 実装（1タスクずつ）
Phase 5b: /codex-impl-review         ← タスクごとに Codex 厳格レビュー
Phase 6:  /codex-review              ← 最終の汎用レビュー（任意）
Phase 7:  /handover                  ← セッション終了前
Phase 8:  /retro                     ← 振り返り
```

---

## スラッシュコマンド一覧

### Claude 実行コマンド（Claude Code が直接実行）

| コマンド | Phase | 説明 | 引数 |
|---|---|---|---|
| `/research` | 1 | research.md 作成（全ファイル分析 + データフロー + 依存関係） | 目的種別（開発/不具合/更新、省略可） |
| `/plan` | 2 | plan.md + tasks.md 作成 | 機能の説明（**必須**） |
| `/implement` | 5 | tasks.md に従って1タスクずつ実装 | タスク番号（省略で次の未完了を自動選択） |

### Codex レビューコマンド（Codex CLI 経由）

| コマンド | Phase | 説明 | 引数 |
|---|---|---|---|
| `/codex-research-review` | 1b | research.md の Codex クロスレビュー（1サイクル） | 機能名（省略可） |
| `/codex-plan-review` | 4 | plan.md/tasks.md の Codex クロスレビューサイクル | 機能名（省略可） |
| `/codex-impl-review` | 5b | 実装の Codex 厳格レビュー | タスク説明, ファイルパス（省略可） |
| `/codex-review` | 6 | 汎用コードレビュー（変更差分を Codex に送信） | 追加指示（省略可） |

### セッション管理コマンド

| コマンド | Phase | 説明 | 引数 |
|---|---|---|---|
| `/handover` | 7 | セッション引き継ぎ文書の生成・更新 | 追加コンテキスト（省略可） |
| `/retro` | 8 | セッション振り返りと KNOWLEDGE.md 更新 | 追加コンテキスト（省略可） |

---

## research.md の必須分析項目

`/research` で生成される research.md には以下を必ず含めること:

1. **各ファイルの役割と内部実装** — 関数シグネチャだけでなく内部ロジックまで
2. **モジュール間依存グラフ** — import 関係、相互参照
3. **スクリプト間データフロー** — 引数の型・構造、コールバックシグネチャ、設定値の伝播経路
4. **重要な変数の行き来** — 各スクリプト間で受け渡される変数名・型・デフォルト値
5. **ファイル I/O の構造** — JSON/CSV のフィールド名と型、チェックポイント形式
6. **存在しないが必要なもの** — 統合時に必要だが未実装のメソッド/パラメータ
7. **潜在的なバグ・リスク** — 事実と推測を区別

---

## プレースホルダ一覧

| プレースホルダ | 用途 | 使用ファイル |
|---|---|---|
| `$ARGUMENTS` | コマンド引数（ユーザー入力） | 全 .claude/commands/*.md |
| `$FEATURE` | 機能名・機能説明 | codex_research_review.md, codex_plan_review.md |
| `$TASK_DESCRIPTION` | タスクの説明 | codex_impl_review.md |
| `$FILE_LIST` | 対象ファイルパス（カンマ区切り） | codex_impl_review.md |
| `{{LANG}}` | 言語/フレームワーク名 | master_workflow.md, codex_impl_review.md |
| `{{VERIFY_CMD}}` | 検証コマンド | master_workflow.md, implement.md |
| `{{LANG_RULES}}` | 言語固有のレビュールール | codex_impl_review.md |

---

## セッション管理

レビューセッションは `.agents/sessions.json` で管理されます。

---

## 関連ファイル

| ファイル | 役割 |
|---|---|
| `.agents/master_workflow.md` | マスター手順書（全フェーズのプロンプトとルール） |
| `.agents/prompts/codex_*.md` | Codex 送信用プロンプトテンプレート |
| `.agents/workflows/codex_review.md` | 汎用レビューワークフロー |
| `.agents/workflows/handover.md` | Handover ワークフロー定義 |
| `.agents/workflows/retro.md` | Retro ワークフロー定義 |
| `.agents/sessions.json` | セッションID管理 |
| `.context/research.md` | プロジェクト分析結果 |
| `.context/plan.md` | 実装計画 |
| `.context/tasks.md` | タスク一覧（チェックリスト） |
| `.context/HANDOVER.md` | 引き継ぎ文書 |
| `.context/KNOWLEDGE.md` | 蓄積された知見 |
