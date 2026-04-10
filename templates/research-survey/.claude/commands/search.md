---
description: "Phase 2: 文献検索（Web 検索で論文を収集し reading list を構築）"
---

# 文献検索

## 入力

- `$ARGUMENTS`: 追加の検索指示（省略可）
  - 例: `/search 2023年以降の diffusion model に絞って追加検索`

## 前提

- `.claude/context/scope.md` が存在すること（存在しない場合はユーザーに通知）
- `.claude/context/available_tools.md` を参照し利用可能なツールを確認（存在しない場合は WebSearch のみ使用）

## 研究分野情報

- **ドメイン**: {{DOMAIN}}
- **主要会議・ジャーナル**: {{KEY_VENUES}}

## プロンプト

scope.md の検索キーワードと対象会議・ジャーナルをもとに、関連論文を網羅的に収集してください。

## ツール選択（優先度順）

### 1. WebSearch（常に利用可能）

scope.md の検索クエリ例を使って WebSearch を実行:
- `"keyword1 keyword2" site:arxiv.org`
- `"keyword" CVPR 2024`
- `"keyword" survey OR review`

### 2. PaperQA2（available_tools.md で ✓ の場合）

```bash
pqa search "keyword1 keyword2" --limit 20
```

### 3. paper-search-mcp（MCP 利用可能 かつ 上記 CLI なしの場合のみ）

`search_papers` ツールで 24 ソース横断検索。

## 検索手順

1. **キーワード検索**: scope.md の検索クエリを実行（3-5 パターン）
2. **会議・ジャーナル検索**: 主要会議の proceedings を確認
3. **引用追跡（snowball）**: 重要論文の参考文献リストから追加候補を特定
4. **重複排除**: 同一論文の重複を除去

### 並行検索パターン（推奨）

検索クエリが3つ以上ある場合、Agent ツールで Sonnet subagent を並行起動し、各クエリを同時に検索:

```
Agent(sonnet-paper-research) × N 本並行:
  - Agent 1: キーワードセット A で WebSearch
  - Agent 2: キーワードセット B で WebSearch
  - Agent 3: 会議名 × キーワードで WebSearch
→ Claude 本体が結果を統合・重複排除
```

## 各論文の収集情報

| フィールド | 説明 |
|------------|------|
| ID | 連番（P001, P002, ...） |
| タイトル | 論文タイトル |
| 著者 | 第一著者 + et al. |
| 年 | 出版年 |
| 会議/ジャーナル | 発表先 |
| URL | アクセス可能な URL（arxiv, DOI 等） |
| 概要 | 1-2文の要約（検索結果から） |
| 関連 RQ | scope.md のどの RQ に関連するか |
| 優先度 | High / Medium / Low |

## ルール

- 最低 20 件を目標に検索する（トピックの規模に応じて調整）
- scope.md の包含・除外基準に従う
- **存在しない論文を捏造しない** — 検索結果に基づく論文のみ記載
- URL は検索で実際に見つかったもののみ記載
- 同じ検索クエリを繰り返さない — 結果が少ない場合はキーワードを変えて再検索

## 出力

`.claude/context/papers.md` — 以下の構成:

```markdown
# Reading List

## 検索サマリー
- 実行した検索クエリ一覧
- 使用ツール（WebSearch / PaperQA2 / paper-search-mcp）
- 検索結果の統計（総件数、会議別、年代別）

## 論文一覧
### High Priority
（表形式で論文を列挙）

### Medium Priority
（表形式で論文を列挙）

### Low Priority
（表形式で論文を列挙）
```

## 次のステップ

> papers.md を確認してください。
> 追加検索が必要な場合は `/search <追加指示>` を実行してください。
> 問題なければ `/read` で論文分析に進んでください。
