---
description: "Phase 6: サーベイ品質レビュー（カバレッジ・整合性・引用実在検証）"
---

# サーベイ品質レビュー

## 入力

- `$ARGUMENTS`: レビュー観点の追加指示（省略可）

## 前提

- `.claude/context/draft.md` が存在すること
- `.claude/context/scope.md` が存在すること
- `.claude/context/outline.md` が存在すること
- `.claude/context/notes.md` が存在すること（Paper Card 形式）
- `.claude/context/available_tools.md` を参照し利用可能なツールを確認

## 研究分野情報

- **ドメイン**: {{DOMAIN}}

## プロンプト

draft.md のサーベイ全体を以下の観点でレビューし、問題点と改善提案を報告してください。

## レビュー観点

### 1. RQ カバレッジ
- scope.md の各 RQ がサーベイ内で回答されているか
- 回答が不十分な RQ はどれか
- 追加の論文調査が必要か

### 2. 引用実在検証（重要）

**LLM の引用ハルシネーション率は 18-55%。全引用を検証すること。**

#### 検証フロー

```
1. draft.md から全 \cite{key} を抽出
2. 各 key について notes.md の Paper Card と照合:
   a. Paper Card に存在 かつ Citation Verified: ✓ → ✓ Verified
   b. Paper Card に存在 かつ Citation Verified: ✗ → 要検証
   c. Paper Card に存在しない → ✗ Unknown（draft 執筆中に追加された引用）

3. 要検証 / Unknown の引用について:
```

#### ツール選択（優先度順）

**semanticscholar Python**（available_tools.md で ✓ の場合）:
```bash
python -c "
from semanticscholar import SemanticScholar
s = SemanticScholar()
r = s.search_paper('PAPER_TITLE', limit=1)
if r.items:
    p = r.items[0]
    print(f'✓ {p.title} ({p.year}) - ID: {p.paperId}')
else:
    print('✗ NOT FOUND')
"
```

**Fallback**: WebSearch `"論文タイトル" site:semanticscholar.org OR site:scholar.google.com`

#### 検証結果レポート

```markdown
## 引用検証結果

| BibTeX Key | タイトル | 状態 | Semantic Scholar ID |
|------------|---------|------|---------------------|
| he2016deep | Deep Residual Learning... | ✓ Verified | abc123 |
| unknown2024 | ... | ✗ Not Found | — |

- ✓ Verified: X 件
- ✗ Not Found: Y 件（要修正）
- ? Ambiguous: Z 件（手動確認推奨）
```

### 3. 引用の内部整合性
- 本文中の `\cite{key}` が References セクションに全て存在するか
- References に本文で引用されていない論文がないか（孤立引用）
- 引用された数値・結果が notes.md の Paper Card と一致するか

### 4. 論理構成
- セクション間の流れは論理的か
- 議論の飛躍や唐突な話題転換はないか
- Introduction で提示した構成と実際の構成は一致しているか

### 5. 網羅性
- 重要な手法・論文が漏れていないか
- 特定の年代やアプローチに偏りがないか
- Discussion で十分な横断的分析が行われているか

### 6. 表記・品質
- 用語の一貫性（同じ概念に異なる名称を使っていないか）
- 表・比較の正確性
- Figure プレースホルダの適切性

### ドメイン固有チェック

{{SURVEY_RULES}}

## 出力形式

```markdown
# サーベイレビュー結果

## サマリー
- 全体評価: （良好 / 要修正 / 大幅修正）
- 主要な問題点: X 件

## 引用検証結果
（上記の表形式）

## RQ カバレッジ
| RQ | カバー状況 | 改善案 |
|----|------------|--------|

## 構成・論理
- 問題箇所と改善提案

## 網羅性
- 不足しているトピック・論文

## 修正アクション（優先度順）
1. [P0] ...（引用が存在しない等）
2. [P1] ...
3. [P2] ...
```

レビュー完了後、P0/P1 の修正を自動で draft.md に適用する。P2 はユーザーに判断を仰ぐ。

## 出力

- `.claude/context/review.md` — レビュー結果
- `.claude/context/draft.md` — P0/P1 修正を適用

## 次のステップ

> review.md を確認してください。
> 追加修正が必要な場合は直接指示してください。
> 問題なければ `/convert` で LaTeX 変換に進んでください。
