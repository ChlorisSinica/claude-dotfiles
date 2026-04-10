# 研究サーベイ マスター手順書

**使用モデル**: Opus 4.6
**研究ドメイン**: {{DOMAIN}}

---

## ツール階層

1. **WebSearch / WebFetch**（組み込み）— 常に利用可能
2. **CLI ツール** — `available_tools.md` で ✓ のものを使用
3. **MCP** — CLI 代替がない場合のみ

詳細は `.claude/agents/tools.md` 参照。初回は `/check-tools` でツール状況を確認推奨。

---

## 全体フロー

```
Phase 0:   /check-tools                ← ツール検出（初回推奨）
Phase 1:   /scope <topic>              ← 研究スコープ定義（RQ、キーワード、基準）
Phase 2:   /search                     ← 文献検索（WebSearch / PaperQA2）
Phase 3:   /read [論文ID]              ← 論文分析（Paper Card 作成 + 反復 outline 更新）
Phase 4:   /outline                    ← サーベイ構成案の最終化
Phase 5:   /draft [セクション番号]      ← セクションごとに執筆
Phase 6:   /review                     ← 品質レビュー（引用実在検証を含む）
           /convert                    ← Markdown → LaTeX 変換（任意のタイミング）
Phase 7:   /handover                   ← セッション引き継ぎ
```

### フェーズ間の依存関係

```
scope → search → read ──→ outline → draft → review → convert
                  │  ↑        ↑                ↑
                  │  └─ 5本ごとに              │
                  │     draft_outline 更新      │
                  │                             │
                  └── ギャップ発見で search に戻る ┘
```

---

## 核心設計: Paper Card（IterSurvey 準拠）

/read で各論文を構造化 Paper Card に蒸留する。全文コピーではなく核心情報のみ:

```markdown
## P001: [タイトル]
- **BibTeX Key**: `authorYYYYkeyword`
- **Authors**: First Author et al., YYYY
- **Venue**: Conference/Journal YYYY
- **URL**: https://...
- **Contribution**: 1-2文で主要貢献
- **Method**: 手法の核心
- **Key Results**: 定量的結果（ベンチマーク、メトリクス、数値）
- **Limitations**: 限界・課題
- **Relations**: 先行研究との差分、後続研究への影響
- **RQ**: 関連 RQ 番号
- **Citation Verified**: ✓/✗ (Semantic Scholar ID)
```

**利点:**
- /draft は Paper Card のみ参照（全文再読不要）
- BibTeX Key が早期に確定 → 引用の一貫性
- Citation Verified で引用ハルシネーションを防止

---

## 核心設計: 反復的アウトライン更新

```
静的アプローチ（従来）:
  search → read（全部読む）→ outline → draft

反復アプローチ（本システム）:
  search → read（5本ごとに draft_outline を更新）→ outline（最終化）→ draft
```

- /read が Paper Card を5本追記するたびに `draft_outline.md` を更新
- /outline は draft_outline.md を最終化
- ギャップ発見時は /search に戻る

---

## 核心設計: 引用実在検証

LLM の引用ハルシネーション率は 18-55%。対策:

1. **/read 時**: Paper Card 作成時に Semantic Scholar API で実在確認（先行検証）
2. **/review 時**: draft.md の全 `\cite{key}` を notes.md と照合、未検証分を追加検証
3. **ツール**: semanticscholar Python (CLI) → WebSearch (fallback)

---

## フェーズ別ツールマッピング

| Phase | 主要ツール（組み込み/CLI） | MCP（代替なし時のみ） |
|-------|--------------------------|----------------------|
| /search | WebSearch + `pqa search` | paper-search-mcp |
| /read | WebFetch + `paper`(arxiv-dl) + `marker_single` + Read | arxiv-mcp-server |
| /draft | Paper Card 参照 + `pqa ask`（事実確認） | — |
| /review | `semanticscholar` + WebSearch（引用検証） | — |
| /convert | Pandoc + `bibcure` | — |

---

## 並行処理パターン

`sonnet-paper-research` subagent を使った並行処理:

- **/search**: 複数キーワードセットを並行検索
- **/read all**: 論文を3-5本ずつバッチに分割し並行分析

subagent は Paper Card 作成 + 引用検証のみ。outline 更新は Claude 本体が行う。

---

## ドメイン固有ルール

{{SURVEY_RULES}}

---

## 成果物一覧

| ファイル | フェーズ | 説明 |
|----------|----------|------|
| `.claude/context/available_tools.md` | 0 | ツール検出結果 |
| `.claude/context/scope.md` | 1 | 研究スコープ |
| `.claude/context/papers.md` | 2 | reading list |
| `.claude/context/notes.md` | 3 | Paper Card 集 |
| `.claude/context/draft_outline.md` | 3 | 暫定構成（反復更新） |
| `.claude/context/outline.md` | 4 | サーベイ構成案（最終） |
| `.claude/context/draft.md` | 5 | サーベイ本文 |
| `.claude/context/review.md` | 6 | レビュー結果 |
| `output/survey.tex` | convert | LaTeX ファイル |
| `output/references.bib` | convert | BibTeX ファイル |
| `.claude/context/HANDOVER.md` | 7 | セッション引き継ぎ |
