---
description: "汎用コードレビュー: 変更を Codex に送って自動レビュー→修正適用"
---

# Codex Code Review

既存の `.agents/workflows/codex_review.md` ワークフローを実行してください。

## 手順

1. 変更状態を確認:
```bash
git status --short
```

2. 変更がない場合はユーザーに通知して終了

3. Codex にレビューを依頼し、セッションIDを記録:
```bash
review_output=$(codex review "Check for best practices, potential bugs, and stylistic issues. $ARGUMENTS")
echo "$review_output"

session_id=$(echo "$review_output" | grep -oE '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)
if [ -n "$session_id" ]; then
    sessions_file=".agents/sessions.json"
    if [ -f "$sessions_file" ]; then
        tmp=$(cat "$sessions_file" | python3 -c "import sys,json; d=json.load(sys.stdin); d['last_review']='$session_id'; print(json.dumps(d,indent=2))")
    else
        tmp="{\"last_review\": \"$session_id\"}"
    fi
    echo "$tmp" > "$sessions_file"
    echo "Session ID: $session_id"
fi
```

4. レビュー指摘がある場合、Codex に修正を適用させる:
```bash
sessions_file=".agents/sessions.json"
session_id=$(cat "$sessions_file" | python3 -c "import sys,json; print(json.load(sys.stdin).get('last_review',''))")
if [ -n "$session_id" ]; then
    codex exec resume --full-auto "$session_id" "Please apply the suggested fixes from the review to the codebase."
fi
```

5. 修正結果を確認:
```bash
git diff
```

6. 結果をユーザーに報告し、追加の修正が必要か確認
