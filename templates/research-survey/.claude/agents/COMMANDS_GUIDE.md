# 研究サーベイ コマンドガイド

## 概要

Claude Code のスラッシュコマンドと CLI ツールを組み合わせ、論文サーベイの文献検索・分析・執筆・レビューを効率化します。

---

## 全体の流れ

```
Phase 0:   /check-tools                ← ツール検出（初回推奨）
Phase 1:   /scope <topic>              ← 研究スコープ定義
Phase 2:   /search                     ← 文献検索
Phase 3:   /read [論文ID]              ← 論文分析（Paper Card + 反復 outline）
Phase 4:   /outline                    ← サーベイ構成案の最終化
Phase 5:   /draft [セクション番号]      ← 執筆
Phase 6:   /review                     ← 品質レビュー（引用実在検証）
           /convert                    ← Markdown → LaTeX 変換
Phase 7:   /handover                   ← セッション引き継ぎ
```

---

## スラッシュコマンド一覧

| コマンド | Phase | 説明 | 引数 |
|---|---|---|---|
| `/check-tools` | 0 | 利用可能ツールの検出・記録 | — |
| `/scope` | 1 | RQ、キーワード、包含/除外基準を定義 | 研究トピック（**必須**） |
| `/search` | 2 | WebSearch/PaperQA2 で論文を収集 | 追加検索指示（省略可） |
| `/read` | 3 | Paper Card 作成 + 反復 outline 更新 | 論文ID（省略で High Priority を順に） |
| `/outline` | 4 | draft_outline を最終化 | 構成指示（省略可） |
| `/draft` | 5 | Paper Card を参照してセクション執筆 | セクション番号（省略で次の未執筆） |
| `/review` | 6 | カバレッジ・引用実在検証 | レビュー観点（省略可） |
| `/convert` | — | Pandoc + bibcure で LaTeX 変換 | — |
| `/handover` | 7 | セッション引き継ぎ文書の生成 | 追加コンテキスト（省略可） |

---

## ツール優先度

1. **WebSearch / WebFetch**（組み込み）— 常に利用可能
2. **CLI ツール** — available_tools.md で ✓ のものを使用
3. **MCP** — CLI 代替がない場合のみ

| CLI ツール | 用途 | インストール |
|---|---|---|
| PaperQA2 | 論文検索・QA | `pip install paper-qa>=5` |
| arxiv-dl | arXiv/会議論文DL + BibTeX | `pip install arxiv-dl` |
| marker-pdf | PDF→Markdown 変換 | `pip install marker-pdf` |
| semanticscholar | 引用実在検証 | `pip install semanticscholar` |
| bibcure | BibTeX 正規化 | `pip install bibcure` |
| Pandoc | Markdown→LaTeX | `winget install --id JohnMacFarlane.Pandoc` |

一括: `pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure`

---

## プレースホルダ一覧

| プレースホルダ | 用途 | 使用ファイル |
|---|---|---|
| `$ARGUMENTS` | コマンド引数（ユーザー入力） | 全 commands/*.md |
| `{{DOMAIN}}` | 研究ドメイン名 | 全テンプレート |
| `{{KEY_VENUES}}` | 主要会議・ジャーナル | scope.md, search.md |
| `{{DOMAIN_KEYWORDS}}` | 分野固有キーワード | scope.md, master_workflow.md |
| `{{SURVEY_RULES}}` | ドメイン固有のサーベイルール | read.md, outline.md, draft.md, review.md |

---

## 成果物一覧

| ファイル | 役割 |
|---|---|
| `.claude/context/available_tools.md` | ツール検出結果 |
| `.claude/context/scope.md` | 研究スコープ（RQ、キーワード、基準） |
| `.claude/context/papers.md` | reading list（論文一覧） |
| `.claude/context/notes.md` | Paper Card 集（構造化ノート） |
| `.claude/context/draft_outline.md` | 暫定構成（/read で反復更新） |
| `.claude/context/outline.md` | サーベイ構成案（最終） |
| `.claude/context/draft.md` | サーベイ本文 |
| `.claude/context/review.md` | レビュー結果（引用検証含む） |
| `output/survey.tex` | LaTeX ファイル |
| `output/references.bib` | BibTeX ファイル |
| `.claude/context/HANDOVER.md` | セッション引き継ぎ |

---

## 関連ファイル

| ファイル | 役割 |
|---|---|
| `.claude/agents/master_workflow.md` | マスター手順書（全フェーズ + 設計思想） |
| `.claude/agents/tools.md` | ツール設定ガイド |
| `.claude/agents/sonnet-paper-research.md` | 並行論文分析 subagent |
| `.claude/agents/sessions.json` | セッション管理 |
