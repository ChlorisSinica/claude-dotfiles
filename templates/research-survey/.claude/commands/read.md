---
description: "Phase 3: 論文分析（Paper Card 形式の構造化ノート作成 + 反復アウトライン更新）"
---

# 論文分析

## 入力

- `$ARGUMENTS`: 対象論文の指定（省略可）
  - 空の場合: papers.md の High Priority 論文を順に分析
  - 例: `/read P001,P003,P007` — 指定 ID の論文を分析
  - 例: `/read all` — 全論文を分析（並行処理）

## 前提

- `.claude/context/papers.md` が存在すること
- `.claude/context/scope.md` が存在すること（RQ 参照用）
- `.claude/context/available_tools.md` を参照し利用可能なツールを確認

## 研究分野情報

- **ドメイン**: {{DOMAIN}}

## ツール選択（優先度順）

### 論文情報の取得

1. **WebFetch**（常に利用可能）— arxiv abs ページ、論文 HTML 版から取得
2. **arxiv-dl CLI**（available_tools.md で ✓ の場合）:
   ```bash
   paper <arxiv-id>  # PDF + BibTeX をダウンロード
   ```
3. **marker-pdf CLI**（available_tools.md で ✓ の場合）:
   ```bash
   marker_single <downloaded.pdf> --output_dir .claude/context/papers/
   ```
4. **Read ツール** — ダウンロード済み PDF を直接読む
5. **arxiv-mcp-server**（MCP 利用可能 かつ 上記 CLI なしの場合のみ）

### 引用検証

1. **semanticscholar Python**（available_tools.md で ✓ の場合）:
   ```bash
   python -c "
   from semanticscholar import SemanticScholar
   s = SemanticScholar()
   r = s.search_paper('PAPER_TITLE', limit=1)
   if r.items: print(f'ID: {r.items[0].paperId}')
   else: print('NOT FOUND')
   "
   ```
2. **Fallback**: WebSearch `"論文タイトル" site:semanticscholar.org`

## Paper Card 形式（必須）

各論文を以下の形式で蒸留する。**全文コピーではなく、核心情報のみ**:

```markdown
## P001: [タイトル]
- **BibTeX Key**: `authorYYYYkeyword`（例: `he2016deep`）
- **Authors**: First Author et al., YYYY
- **Venue**: Conference/Journal YYYY
- **URL**: https://...
- **Contribution**: 1-2文で主要貢献を記述
- **Method**: 手法の核心（アーキテクチャ、アルゴリズム、定式化の要点）
- **Key Results**: 定量的結果（ベンチマーク名、メトリクス、数値）
- **Limitations**: 著者が述べている限界、または読み取れる課題
- **Relations**: 先行研究との差分、後続研究への影響
- **RQ**: 関連する RQ 番号（scope.md 参照）
- **Citation Verified**: ✓/✗ (Semantic Scholar ID: xxx / 未検証)
```

### BibTeX Key 命名規則

`{第一著者の姓(小文字)}{年}{キーワード}` — 例: `he2016deep`, `vaswani2017attention`

## 反復アウトライン更新

**Paper Card を 5 本作成するごとに**、`.claude/context/draft_outline.md` を更新する:

1. 初回: scope.md の初期構成案をベースに draft_outline.md を作成
2. 以降: 新しい Paper Card の内容を踏まえてセクション構成・論文割り当てを更新
3. 更新時に「このセクションのカバーが薄い」「新しいテーマが見えてきた」等の気づきを `## ギャップメモ` セクションに記録

```markdown
# Draft Outline（暫定構成）

更新: YYYY-MM-DD（P001-P010 分析後）

## 1. Introduction
- 割り当て: P001, P005

## 2. Background
- 割り当て: P002, P003

## 3. [テーマA]
- 割り当て: P004, P006, P007
...

## ギャップメモ
- セクション3のカバーが薄い（3本のみ）→ 追加検索推奨
- P008 が新テーマを示唆 → セクション追加を検討
```

## 並行分析パターン（/read all 時）

`$ARGUMENTS` が `all` の場合、Agent ツールで sonnet-paper-research subagent を並行起動:

```
1. papers.md の全論文リストを取得
2. 3-5 本ずつバッチに分割
3. 各バッチを sonnet-paper-research subagent に委託（並行起動）
   - subagent に scope.md の RQ リストを渡す
   - subagent に利用可能ツール情報を渡す
4. subagent が Paper Card を返却
5. Claude 本体が:
   a. notes.md に統合（重複排除）
   b. 品質チェック（Paper Card の完全性）
   c. draft_outline.md を更新
```

## ルール

- 論文の内容を正確に記述する — 推測は「（推測）」と明記
- アクセスできなかった論文は「アクセス不可」と記載し、スキップ
- 他論文との関係は papers.md 内の論文に限定しない（外部の重要論文も含む）
- {{SURVEY_RULES}}

## 出力

- `.claude/context/notes.md` — Paper Card の集合
- `.claude/context/draft_outline.md` — 暫定構成（反復更新）

既に notes.md が存在する場合は、未分析の論文を追記する（既存の分析は保持）。

## 次のステップ

> notes.md を確認してください。
> 追加の論文分析が必要な場合は `/read <論文ID>` を実行してください。
> draft_outline.md のギャップメモを確認し、追加検索が必要なら `/search` へ。
> 問題なければ `/outline` でサーベイ構成案の最終化に進んでください。
