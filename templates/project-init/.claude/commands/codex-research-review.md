---
description: "§1 research.md の Codex クロスレビュー（1サイクル）: 不足分の補完と更新"
---

# Codex Research Review

research.md の Codex クロスレビューを1サイクル実行してください。

## 前提

- Claude が `.context/research.md` を既に作成済みであること

## 手順

1. `.context/research.md` を読み込み、内容を確認

2. `.agents/prompts/codex_research_review.md` のプロンプトテンプレートを読み込む

3. テンプレート内の `$FEATURE` を置換（`$ARGUMENTS` が空なら research.md の概要から推定）

4. プロンプトと research.md を結合して Codex に送信:
```powershell
$prompt = Get-Content ".agents/prompts/codex_research_review.md" -Raw
$prompt = $prompt -replace '\$FEATURE', '$ARGUMENTS'
$research = Get-Content ".context/research.md" -Raw
"$prompt`n`n---`n`n# research.md`n$research" | codex review -
```

5. Codex のレビュー結果に基づき `.context/research.md` を更新

6. **1サイクルで終了**（plan/impl レビューと異なり、繰り返さない）

## 注意

- 既存の research.md を削除しない — レビュー結果と不足分で更新する
- 事実と推測を区別し、不確かな箇所は「要確認」とマークする
